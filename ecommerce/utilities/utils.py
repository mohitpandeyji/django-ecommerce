import rules


def add_perm(name, pred):
    """
    Use this method instead of rules.add_perm. Returns the given name for a cleaner syntax when adding rules.
    """
    rules.add_perm(name, pred)
    return name
