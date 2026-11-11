"""Password hashing: salted scrypt, verified in constant time."""

from zimpasta.model.accounts.passwords import (
    check_against_nothing,
    hash_password,
    verify_password,
)


def test_a_hash_verifies_only_its_own_password():
    stored = hash_password("correct horse battery")

    assert stored.startswith("scrypt$16384$8$1$")
    assert "correct horse" not in stored
    assert verify_password("correct horse battery", stored)
    assert not verify_password("correct horse batterY", stored)


def test_the_same_password_gets_a_different_salt_each_time():
    assert hash_password("same password") != hash_password("same password")


def test_malformed_or_foreign_hashes_never_match():
    for stored in ["", "plain", "bcrypt$1$2$3$4$5", "scrypt$x$8$1$AAAA$AAAA", "scrypt$1$2"]:
        assert not verify_password("anything", stored)


def test_checking_an_unknown_user_takes_a_real_check():
    check_against_nothing("whatever")  # completes without raising
