from worker.domain.extraction.stemming_fr import stem_fr


def test_stem_fr_maps_inflected_forms_to_the_same_stem() -> None:
    assert stem_fr("mangeait")[0] == stem_fr("manger")[0]


def test_stem_fr_tokenizes_and_lowercases() -> None:
    stems = stem_fr("Les Chats Mangent")
    assert len(stems) == 3
    assert stems == [stem.lower() for stem in stems]
