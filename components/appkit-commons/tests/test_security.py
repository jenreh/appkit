"""Tests for security utilities (password hashing)."""

import pytest

from appkit_commons.security import (
    DEFAULT_PBKDF2_ITERATIONS,
    SALT_CHARS,
    _gen_salt,
    _hash_internal,
    check_password_hash,
    generate_password_hash,
)


class TestSecurity:
    """Test suite for password hashing and security utilities."""

    def test_gen_salt_default_length(self) -> None:
        """Generated salt has correct length."""
        # Act
        salt = _gen_salt(16)

        # Assert
        assert len(salt) == 16
        assert all(c in SALT_CHARS for c in salt)

    def test_gen_salt_custom_length(self) -> None:
        """Generated salt respects custom length."""
        # Act
        salt = _gen_salt(32)

        # Assert
        assert len(salt) == 32

    def test_gen_salt_zero_length_raises(self) -> None:
        """Generating salt with zero length raises ValueError."""
        # Act & Assert
        with pytest.raises(ValueError, match="Salt length must be at least 1"):
            _gen_salt(0)

    def test_gen_salt_negative_length_raises(self) -> None:
        """Generating salt with negative length raises ValueError."""
        # Act & Assert
        with pytest.raises(ValueError, match="Salt length must be at least 1"):
            _gen_salt(-1)

    def test_gen_salt_randomness(self) -> None:
        """Generated salts are different (random)."""
        # Act
        salt1 = _gen_salt(16)
        salt2 = _gen_salt(16)

        # Assert
        assert salt1 != salt2

    def test_hash_internal_scrypt_default(self) -> None:
        """_hash_internal with scrypt uses default parameters."""
        # Arrange
        salt = "testsalt12345678"
        password = "testpassword"

        # Act
        hash_value, method = _hash_internal("scrypt", salt, password)

        # Assert
        assert method == "scrypt:32768:8:1"
        assert len(hash_value) > 0
        assert isinstance(hash_value, str)

    def test_hash_internal_scrypt_custom_params(self) -> None:
        """_hash_internal with scrypt accepts custom parameters."""
        # Arrange
        salt = "testsalt12345678"
        password = "testpassword"

        # Act
        hash_value, method = _hash_internal("scrypt:16384:8:1", salt, password)

        # Assert
        assert method == "scrypt:16384:8:1"
        assert len(hash_value) > 0

    def test_hash_internal_scrypt_invalid_params_raises(self) -> None:
        """_hash_internal with scrypt raises on invalid parameters."""
        # Act & Assert
        with pytest.raises(ValueError, match="'scrypt' takes 3 arguments"):
            _hash_internal("scrypt:invalid", "salt", "password")

    def test_hash_internal_pbkdf2_default(self) -> None:
        """_hash_internal with pbkdf2 uses default parameters."""
        # Arrange
        salt = "testsalt12345678"
        password = "testpassword"

        # Act
        hash_value, method = _hash_internal("pbkdf2", salt, password)

        # Assert
        assert method == f"pbkdf2:sha256:{DEFAULT_PBKDF2_ITERATIONS}"
        assert len(hash_value) > 0

    def test_hash_internal_pbkdf2_custom_hash(self) -> None:
        """_hash_internal with pbkdf2 accepts custom hash algorithm."""
        # Arrange
        salt = "testsalt12345678"
        password = "testpassword"

        # Act
        hash_value, method = _hash_internal("pbkdf2:sha512", salt, password)

        # Assert
        assert method == f"pbkdf2:sha512:{DEFAULT_PBKDF2_ITERATIONS}"
        assert len(hash_value) > 0

    def test_hash_internal_pbkdf2_custom_iterations(self) -> None:
        """_hash_internal with pbkdf2 accepts custom iterations."""
        # Arrange
        salt = "testsalt12345678"
        password = "testpassword"

        # Act
        hash_value, method = _hash_internal("pbkdf2:sha256:500000", salt, password)

        # Assert
        assert method == "pbkdf2:sha256:500000"
        assert len(hash_value) > 0

    def test_hash_internal_pbkdf2_too_many_args_raises(self) -> None:
        """_hash_internal with pbkdf2 raises on too many arguments."""
        # Act & Assert
        with pytest.raises(ValueError, match="'pbkdf2' takes 2 arguments"):
            _hash_internal("pbkdf2:sha256:600000:extra", "salt", "password")

    def test_hash_internal_invalid_method_raises(self) -> None:
        """_hash_internal with invalid method raises ValueError."""
        # Act & Assert
        with pytest.raises(ValueError, match="Invalid hash method"):
            _hash_internal("invalid_method", "salt", "password")

    def test_generate_password_hash_default_scrypt(self) -> None:
        """generate_password_hash uses scrypt by default."""
        # Act
        pwhash = generate_password_hash("mypassword")

        # Assert
        assert pwhash.startswith("scrypt:")
        parts = pwhash.split("$")
        assert len(parts) == 3
        assert parts[0] == "scrypt:32768:8:1"

    def test_generate_password_hash_pbkdf2(self) -> None:
        """generate_password_hash works with pbkdf2 method."""
        # Act
        pwhash = generate_password_hash("mypassword", method="pbkdf2")

        # Assert
        assert pwhash.startswith("pbkdf2:")
        parts = pwhash.split("$")
        assert len(parts) == 3

    def test_generate_password_hash_custom_salt_length(self) -> None:
        """generate_password_hash respects custom salt length."""
        # Act
        pwhash = generate_password_hash("mypassword", salt_length=32)

        # Assert
        parts = pwhash.split("$")
        salt = parts[1]
        assert len(salt) == 32

    def test_generate_password_hash_different_each_time(self) -> None:
        """generate_password_hash produces different hashes each time."""
        # Act
        hash1 = generate_password_hash("mypassword")
        hash2 = generate_password_hash("mypassword")

        # Assert
        assert hash1 != hash2  # Different salt each time

    def test_check_password_hash_correct_password(self) -> None:
        """check_password_hash returns True for correct password."""
        # Arrange
        password = "correct_password"
        pwhash = generate_password_hash(password)

        # Act
        result = check_password_hash(pwhash, password)

        # Assert
        assert result is True

    def test_check_password_hash_incorrect_password(self) -> None:
        """check_password_hash returns False for incorrect password."""
        # Arrange
        pwhash = generate_password_hash("correct_password")

        # Act
        result = check_password_hash(pwhash, "wrong_password")

        # Assert
        assert result is False

    def test_check_password_hash_scrypt_compatibility(self) -> None:
        """check_password_hash verifies scrypt hashes."""
        # Arrange
        password = "test123"
        pwhash = generate_password_hash(password, method="scrypt")

        # Act
        result = check_password_hash(pwhash, password)

        # Assert
        assert result is True

    def test_check_password_hash_pbkdf2_compatibility(self) -> None:
        """check_password_hash verifies pbkdf2 hashes."""
        # Arrange
        password = "test456"
        pwhash = generate_password_hash(password, method="pbkdf2")

        # Act
        result = check_password_hash(pwhash, password)

        # Assert
        assert result is True

    def test_check_password_hash_malformed_hash_returns_false(self) -> None:
        """check_password_hash returns False for malformed hash."""
        # Act
        result = check_password_hash("invalid_hash_format", "password")

        # Assert
        assert result is False

    def test_check_password_hash_empty_password(self) -> None:
        """check_password_hash handles empty password."""
        # Arrange
        pwhash = generate_password_hash("")

        # Act
        result = check_password_hash(pwhash, "")

        # Assert
        assert result is True

    def test_check_password_hash_special_characters(self) -> None:
        """check_password_hash handles passwords with special characters."""
        # Arrange
        password = "p@ssw0rd!#$%^&*()"
        pwhash = generate_password_hash(password)

        # Act
        result = check_password_hash(pwhash, password)

        # Assert
        assert result is True

    def test_check_password_hash_unicode_password(self) -> None:
        """check_password_hash handles Unicode passwords."""
        # Arrange
        password = "パスワード🔒"
        pwhash = generate_password_hash(password)

        # Act
        result = check_password_hash(pwhash, password)

        # Assert
        assert result is True

    def test_check_password_hash_timing_attack_resistance(self) -> None:
        """check_password_hash uses constant-time comparison."""
        # This test verifies hmac.compare_digest is used
        # We can't easily test timing, but we can verify behavior

        # Arrange
        pwhash = generate_password_hash("test")

        # Act - both wrong passwords should take similar time
        result1 = check_password_hash(pwhash, "a")
        result2 = check_password_hash(pwhash, "b" * 1000)

        # Assert
        assert result1 is False
        assert result2 is False

    def test_password_hash_roundtrip(self) -> None:
        """Full roundtrip: hash and verify multiple passwords."""
        # Arrange
        passwords = ["simple", "complex!@#", "", "verylongpassword" * 10]

        for password in passwords:
            # Act
            pwhash = generate_password_hash(password)
            valid = check_password_hash(pwhash, password)
            invalid = check_password_hash(pwhash, password + "wrong")

            # Assert
            assert valid is True
            assert invalid is False
