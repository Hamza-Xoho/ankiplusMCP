class CardsError(Exception):
    def __init__(self, code, what, remedy):
        self.code, self.what, self.remedy = code, what, remedy
        super().__init__(f'ERROR {code} {what} — {remedy}')

class Refused(CardsError):
    """A required earlier step has not completed."""
