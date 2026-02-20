
def with_title(e: BaseException, title) -> BaseException:
    setattr(e, 'title', title)
    return e


def get_title(e: BaseException):
    return getattr(e, 'title', None)
