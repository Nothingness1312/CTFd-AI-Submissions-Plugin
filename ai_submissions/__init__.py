import datetime
from urllib.parse import urlparse

from flask import Blueprint, jsonify, render_template, request
from sqlalchemy.exc import IntegrityError

from CTFd.exceptions.challenges import ChallengeSolveException
from CTFd.models import (
    Challenges,
    Fails,
    Partials,
    Ratelimiteds,
    Solves,
    Submissions,
    db,
)
from CTFd.plugins import (
    register_admin_plugin_menu_bar,
    register_admin_plugin_script,
    register_plugin_assets_directory,
    register_plugin_script,
)
from CTFd.plugins.challenges import (
    CHALLENGE_CLASSES,
    CTFdStandardChallenge,
    calculate_value,
)
from CTFd.plugins.challenges.decay import DECAY_FUNCTIONS
from CTFd.plugins.dynamic_challenges import DynamicValueChallenge
from CTFd.utils.decorators import admins_only
from CTFd.utils.user import authed, get_ip, is_admin


class AiLinks(db.Model):
    """
    Stores the "AI Link" (URL) a user submitted alongside a challenge submission.

    This is a plugin-owned table: it is NOT part of the core CTFd schema and is
    created lazily via db.create_all() when the plugin loads.
    """

    __tablename__ = "ai_links"

    id = db.Column(db.Integer, primary_key=True)
    submission_id = db.Column(
        db.Integer, db.ForeignKey("submissions.id", ondelete="CASCADE")
    )
    value = db.Column(db.Text)
    date = db.Column(db.DateTime, default=datetime.datetime.utcnow)

    submission = db.relationship("Submissions", foreign_keys=[submission_id])


class AiSubmissionStandardChallenge(CTFdStandardChallenge):
    """
    Standard challenge subclass that also records the user's AI Link together
    with every submission row (solve / fail / partial / ratelimited).
    """

    # Registers as the "standard" challenge type, overriding the core class.
    id = "standard"
    name = "standard"

    @staticmethod
    def _get_ai_link(request):
        request_data = request.form if not request.is_json else request.get_json() or {}
        return (request_data.get("ai_link") or "").strip()

    @classmethod
    def partial(cls, user, team, challenge, request):
        data = request.form or request.get_json()
        submission = data["submission"].strip()
        ai_link = cls._get_ai_link(request)

        partial = Partials(
            user_id=user.id,
            team_id=team.id if team else None,
            challenge_id=challenge.id,
            ip=get_ip(req=request),
            provided=submission,
        )
        db.session.add(partial)
        db.session.flush()  # Materialize part.id before linking the AI Link row
        db.session.add(AiLinks(submission_id=partial.id, value=ai_link))
        db.session.commit()

    @classmethod
    def ratelimited(cls, user, team, challenge, request):
        data = request.form or request.get_json()
        submission = data["submission"].strip()
        ai_link = cls._get_ai_link(request)

        ratelimited = Ratelimiteds(
            user_id=user.id,
            team_id=team.id if team else None,
            challenge_id=challenge.id,
            ip=get_ip(req=request),
            provided=submission,
        )
        db.session.add(ratelimited)
        db.session.flush()  # Materialize ratelimited.id before linking the AI Link row
        db.session.add(AiLinks(submission_id=ratelimited.id, value=ai_link))
        db.session.commit()

    @classmethod
    def solve(cls, user, team, challenge, request):
        data = request.form or request.get_json()
        submission = data["submission"].strip()
        ai_link = cls._get_ai_link(request)

        solve = Solves(
            user_id=user.id,
            team_id=team.id if team else None,
            challenge_id=challenge.id,
            ip=get_ip(req=request),
            provided=submission,
        )

        try:
            db.session.add(solve)
            db.session.flush()  # Materialize solve.id before linking the AI Link row
            db.session.add(AiLinks(submission_id=solve.id, value=ai_link))
            db.session.commit()
        except IntegrityError as e:
            db.session.rollback()
            raise ChallengeSolveException(
                f"Duplicate solve for user {user.id} on challenge {challenge.id}"
            ) from e

        # If the challenge is dynamic we should calculate a new value
        if challenge.function in DECAY_FUNCTIONS:
            calculate_value(challenge)

    @classmethod
    def fail(cls, user, team, challenge, request):
        data = request.form or request.get_json()
        submission = data["submission"].strip()
        ai_link = cls._get_ai_link(request)

        wrong = Fails(
            user_id=user.id,
            team_id=team.id if team else None,
            challenge_id=challenge.id,
            ip=get_ip(request),
            provided=submission,
        )
        db.session.add(wrong)
        db.session.flush()  # Materialize wrong.id before linking the AI Link row
        db.session.add(AiLinks(submission_id=wrong.id, value=ai_link))
        db.session.commit()


class AiSubmissionDynamicChallenge(DynamicValueChallenge, AiSubmissionStandardChallenge):
    """
    Dynamic challenge subclass. MRO: [AiSubmissionDynamicChallenge,
    DynamicValueChallenge, AiSubmissionStandardChallenge, CTFdStandardChallenge,
    BaseChallenge, object].

    - solve():   DynamicValueChallenge.solve -> super().solve() resolves to
                 AiSubmissionStandardChallenge.solve (stores the AI Link and the
                 solve in one transaction) and then recalculates the value.
    - fail/partial/ratelimited(): resolve (through DynamicValueChallenge, which
                 does not override them) to AiSubmissionStandardChallenge, which
                 records the AI Link as well.
    """

    # Registers as the "dynamic" challenge type, overriding the core class.
    id = "dynamic"
    name = "dynamic"


def validate_and_swap():
    """
    Registered as a before_request handler.

    Two jobs:
    1. Re-assert that CHALLENGE_CLASSES points at the plugin subclasses. This is
       necessary because the core `dynamic_challenges` plugin loads after this
       plugin (alphabetical order) and overwrites CHALLENGE_CLASSES["dynamic"]
       with the un-patched DynamicValueChallenge.
    2. Enforce that every (non-preview) challenge attempt includes a valid AI
       Link, replicating the core validation that was removed when the plugin
       approach was adopted.

    Returning a (jsonify, status) tuple short-circuits the request.
    """
    if CHALLENGE_CLASSES.get("standard") is not AiSubmissionStandardChallenge:
        CHALLENGE_CLASSES["standard"] = AiSubmissionStandardChallenge
    if CHALLENGE_CLASSES.get("dynamic") is not AiSubmissionDynamicChallenge:
        CHALLENGE_CLASSES["dynamic"] = AiSubmissionDynamicChallenge

    if request.method != "POST" or request.path != "/api/v1/challenges/attempt":
        return None

    # Let the core endpoint return 403 for unauthenticated users.
    if not authed():
        return None

    # Admin challenge previews do not produce submissions, so no AI Link needed.
    if is_admin() and request.args.get("preview"):
        return None

    request_data = request.form if not request.is_json else (request.get_json() or {})
    ai_link = (request_data.get("ai_link") or "").strip()

    if not ai_link:
        return (
            jsonify(
                {"success": False, "errors": {"ai_link": ["An AI link is required"]}}
            ),
            400,
        )

    parsed = urlparse(ai_link)
    if parsed.scheme not in ("http", "https") or not parsed.netloc:
        return (
            jsonify(
                {
                    "success": False,
                    "errors": {"ai_link": ["AI link must be a valid URL"]},
                }
            ),
            400,
        )

    return None


admin_ai_submissions = Blueprint(
    "admin_ai_submissions", __name__, template_folder="templates"
)


@admin_ai_submissions.route("/admin/ai-submissions")
@admins_only
def admin_ai_submissions_listing():
    q = request.args.get("q")
    submission_type = request.args.get("type")
    page = abs(request.args.get("page", 1, type=int))

    filters = []
    if submission_type:
        filters.append(Submissions.type == submission_type)
    if q:
        filters.append(
            db.or_(
                AiLinks.value.ilike("%{}%".format(q)),
                Submissions.provided.ilike("%{}%".format(q)),
                Challenges.name.ilike("%{}%".format(q)),
            )
        )

    query = (
        db.session.query(AiLinks)
        .join(Submissions, AiLinks.submission_id == Submissions.id)
        .join(Challenges, Submissions.challenge_id == Challenges.id)
        .filter(*filters)
    )

    pagination = query.order_by(AiLinks.date.desc()).paginate(
        page=page, per_page=50, error_out=False
    )

    return render_template(
        "ai_submissions.html",
        submissions=pagination.items,
        pagination=pagination,
        type=submission_type,
        q=q,
    )


@admin_ai_submissions.route("/admin/ai-submissions/links")
@admins_only
def admin_ai_submissions_links():
    submission_ids = request.args.get("submission_ids", "")
    ids = [i.strip() for i in submission_ids.split(",") if i.strip().isdigit()]
    if not ids:
        return jsonify({})

    rows = (
        db.session.query(AiLinks)
        .filter(AiLinks.submission_id.in_(ids))
        .all()
    )
    return jsonify({str(row.submission_id): row.value for row in rows})


def load(app):
    with app.app_context():
        db.create_all()  # Create the plugin-owned ai_links table if missing

    register_plugin_assets_directory(app, base_path="/plugins/ai_submissions/assets/")
    register_plugin_script("/plugins/ai_submissions/assets/ai_submissions.js")
    register_admin_plugin_script("/plugins/ai_submissions/assets/ai_submissions_admin.js")

    app.register_blueprint(admin_ai_submissions)

    # Initial swap. "standard" survives (the core challenges plugin does not
    # reassign it), while "dynamic" is re-asserted on every request by
    # validate_and_swap() because dynamic_challenges.load() overwrites it later.
    CHALLENGE_CLASSES["standard"] = AiSubmissionStandardChallenge
    CHALLENGE_CLASSES["dynamic"] = AiSubmissionDynamicChallenge

    app.before_request(validate_and_swap)