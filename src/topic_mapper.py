import re

def norm(s):
    return re.sub(r"\s+", " ", str(s).strip().lower())

def detect_subtopic(field, topic, text):
    t = norm(text)

    if field == "physics":
        if any(x in t for x in [
            "rolling without slipping",
            "rolls down without slipping",
            "moment of inertia",
            "rotational kinetic energy",
            "elastic collision",
            "conservation of mechanical energy",
            "conservation of linear momentum"
        ]):
            return "advanced_rigid_body_dynamics"

        if any(x in t for x in [
            "elastic collision",
            "inelastic collision",
            "collision"
        ]):
            return "collision_dynamics"

        if any(x in t for x in [
            "galaxy",
            "planet",
            "moon",
            "gravity",
            "gravitational"
        ]):
            return "gravitational_force"

        if any(x in t for x in [
            "equal and opposite",
            "pushes back",
            "reaction force",
            "exerted by the tree"
        ]):
            return "action_reaction"

        if (
            ("mass" in t or "kg" in t) and
            ("acceleration" in t or "m/s^2" in t or "m/s2" in t) and
            ("force" in t)
        ):
            return "force_mass_acceleration"

        if any(x in t for x in [
            "inertia",
            "at rest",
            "remains in motion",
            "remains at rest"
        ]):
            return "inertia"

        return "general_physics"

    if field == "reading":
        if any(x in t for x in ["main idea", "main purpose", "best title"]):
            return "main_idea"
        if any(x in t for x in ["infer", "imply", "suggest"]):
            return "inference"
        if any(x in t for x in ["tone", "attitude"]):
            return "tone"
        return "general_reading"

    return ""