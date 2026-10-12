import pytest
from scripts.validate_reference_conditioned_replay import confirmation_receipt_ready


def test_incomplete_receipt_does_not_mean_confirmed_data():
    assert not confirmation_receipt_ready({'completed':False,'files':[]})


@pytest.mark.parametrize('rows',[[],[{}]*29,[{}]*28])
def test_completed_flag_cannot_substitute_for_fixed_physical_coverage(rows):
    with pytest.raises(ValueError,match='receipt'):
        confirmation_receipt_ready({'completed':True,'files':rows})
