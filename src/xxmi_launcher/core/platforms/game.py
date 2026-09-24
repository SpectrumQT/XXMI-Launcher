from enum import Enum


class Game(Enum):
    ARKNIGHTS_ENDFIELD = (
        "Arknights Endfield",
        frozenset({"endfield"}),
    )
    GENSHIN_IMPACT = (
        "Genshin Impact",
        frozenset({"genshin"}),
    )
    HONKAI_IMPACT = (
        "Honkai Impact",
        frozenset({"honkai impact"}),
    )
    HONKAI_STAR_RAIL = (
        "Honkai: Star Rail",
        frozenset({"starrail", "star rail"}),
    )
    WUTHERING_WAVES = (
        "Wuthering Waves",
        frozenset({"wuthering"}),
    )
    ZENLESS_ZONE_ZERO = (
        "Zenless Zone Zero",
        frozenset({"zenless"}),
    )

    def __init__(
        self,
        name: str,
        keywords: frozenset[str],
    ):
        self._value_ = name
        self.keywords = keywords
