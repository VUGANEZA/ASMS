class EligibilityResult:
    def __init__(self, allowed, blocked_reason=None, flags=None):
        self.allowed = allowed
        self.blocked_reason = blocked_reason
        self.flags = flags or []

def check_eligibility(intended_use, engine_type, emission_standard=None):
    flags = []
    
    # Rule 1: Only sports or disability use allowed
    if intended_use not in ['sports', 'disability']:
        return EligibilityResult(
            allowed=False,
            blocked_reason=(
                "Second-hand motorcycles are only permitted for sports use "
                "or for persons with disabilities. The stated intended use "
                "does not qualify under current REMA policy."
            )
        )

    # Rule 2: Two-stroke engines only for sports
    if engine_type == 'two_stroke' and intended_use != 'sports':
        return EligibilityResult(
            allowed=False,
            blocked_reason=(
                "Two-stroke motorcycles are only permitted for sports use. "
                "The application states a different intended use."
            )
        )

    # Rule 3: Emission standard — flag, don't block
    if emission_standard:
        try:
            euro_num = int(str(emission_standard).lower().replace('euro', '').strip())
            if euro_num < 4:
                flags.append(
                    f"Emission standard is {emission_standard}, below the "
                    f"recommended Euro 4 minimum. Flagged for officer review."
                )
        except (ValueError, AttributeError):
            flags.append("Emission standard could not be parsed. Flagged for review.")
    else:
        flags.append("No emission standard provided. Flagged for review.")

    return EligibilityResult(allowed=True, flags=flags)