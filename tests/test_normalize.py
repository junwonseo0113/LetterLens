"""Answer validation by field type (app/apply/normalize.py)."""

import pytest

from app.apply.normalize import FieldValueError, normalize


@pytest.mark.parametrize(
    "raw,expected",
    [
        # English
        ("yes", "yes"), ("Yes, married", "yes"), ("no", "no"), ("not married", "no"), ("widowed", "no"),
        # Chinese -- "没有结婚" contains "结婚" (married) but means NOT married
        ("是的", "yes"), ("已婚", "yes"), ("不是", "no"), ("没有结婚", "no"), ("单身", "no"),
        # Korean
        ("네", "yes"), ("예, 결혼했어요", "yes"), ("아니요", "no"), ("아니오", "no"), ("없어요", "no"), ("미혼", "no"),
        # Spanish
        ("sí", "yes"), ("si", "yes"), ("casada", "yes"), ("no", "no"), ("soltero", "no"), ("viuda", "no"),
        # Russian
        ("да", "yes"), ("замужем", "yes"), ("нет", "no"), ("не женат", "no"), ("вдова", "no"),
    ],
)
def test_yes_no_in_every_offered_language(raw, expected):
    assert normalize("yesno", raw) == expected


def test_yes_no_rejects_non_answers():
    with pytest.raises(FieldValueError):
        normalize("yesno", "maybe later")


@pytest.mark.parametrize("raw", ["-500", "−500", "minus 500", "负500", "$ -12.50", "menos 20", "минус 3"])
def test_negative_amounts_are_rejected_not_flipped_positive(raw):
    with pytest.raises(FieldValueError) as exc:
        normalize("money", raw)
    assert exc.value.message_zh == "这里不能是负数。"


@pytest.mark.parametrize(
    "raw,expected",
    [("$1,700.00", "1700"), ("0", "0"), ("none", "0"), ("没有", "0"), ("nada", "0"), ("нет", "0"),
     ("一千七百", "1700"), ("12.50", "12.5")],
)
def test_money(raw, expected):
    assert normalize("money", raw) == expected


@pytest.mark.parametrize("raw,expected", [("1", "1"), ("两个人", "2"), ("three", "3"), ("4 people", "4")])
def test_household_size_is_a_positive_whole_number(raw, expected):
    assert normalize("count", raw) == expected


@pytest.mark.parametrize("raw", ["0", "1.5", "-2", "none", "100"])
def test_household_size_rejects_zero_fractions_negatives_and_absurd_sizes(raw):
    with pytest.raises(FieldValueError):
        normalize("count", raw)


@pytest.mark.parametrize("raw,ok", [("74", True), ("七十四", True), ("0", False), ("74.5", False), ("200", False)])
def test_age(raw, ok):
    if ok:
        assert normalize("age", raw) == "74"
    else:
        with pytest.raises(FieldValueError):
            normalize("age", raw)


def test_application_household_question_uses_count_validation():
    from app.apply.templates import field_spec

    assert field_spec("MSP", "household_size").kind == "count"
    assert field_spec("MSP", "monthly_work_income").kind == "money"
