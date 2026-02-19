
def with_title(e: Exception, title) -> Exception:
    setattr(e, 'title', title)
    return e


def get_title(e: Exception):
    return getattr(e, 'title', None)
