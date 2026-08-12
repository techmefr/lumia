from worker.domain.extraction.stemming_en import stem_en


def test_stem_en_maps_inflected_forms_to_the_same_stem() -> None:
    assert stem_en("running")[0] == stem_en("runs")[0]


def test_stem_en_tokenizes_and_lowercases() -> None:
    stems = stem_en("The Cats Run")
    assert len(stems) == 3
    assert stems == [stem.lower() for stem in stems]
