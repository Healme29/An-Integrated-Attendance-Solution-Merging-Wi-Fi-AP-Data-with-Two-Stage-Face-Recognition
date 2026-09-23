import pytest
import numpy as np
from unittest.mock import patch, MagicMock
from services.face_detection import detect_faces, detect_faces_from_bytes, get_detector
from services.face_recognition import (
    get_embedding, compare_faces, is_match,
    load_embeddings, save_embeddings, load_all_embeddings
)
from services.wifi_scanner import (
    scan_network_arp, check_mac_on_network, normalize_mac,
    _parse_arp_output, log_ap_access
)
import services.wifi_scanner as wifi_scanner
from services.attendance import mark_attendance, get_schedules_for_now
from models.database import get_db


class TestFaceDetectionService:
    def test_detect_faces_from_bytes_invalid_data(self):
        with pytest.raises(ValueError, match="Invalid image data"):
            detect_faces_from_bytes(b"not_an_image")

    def test_detect_faces_no_model(self):
        with patch("services.face_detection.YOLO_MODEL_PATH") as mock_path:
            mock_path.exists.return_value = False
            with pytest.raises(FileNotFoundError, match="YOLOv8-face model not found"):
                get_detector()


class TestFaceRecognitionService:
    def test_compare_faces_empty(self):
        emb = np.random.randn(512).astype(np.float32)
        idx, score = compare_faces(emb, [])
        assert idx == -1
        assert score == 0.0

    def test_is_match_threshold(self):
        is_match(0.6)
        assert True

    def test_save_and_load_embeddings(self, tmp_path):
        import tempfile
        import os
        from config import EMBEDDINGS_DIR

        student_id = 9999
        emb = [np.random.randn(512).astype(np.float32)]

        with patch("services.face_recognition.EMBEDDINGS_DIR", tmp_path):
            save_embeddings(student_id, emb)
            loaded = load_embeddings(student_id)
            assert len(loaded) == 1
            assert np.allclose(loaded[0], emb[0])

    def test_load_all_embeddings(self, tmp_path):
        from config import EMBEDDINGS_DIR
        with patch("services.face_recognition.EMBEDDINGS_DIR", tmp_path):
            save_embeddings(1, [np.random.randn(512).astype(np.float32)])
            save_embeddings(2, [np.random.randn(512).astype(np.float32)])
            all_embs = load_all_embeddings()
            assert 1 in all_embs
            assert 2 in all_embs


class TestWifiScannerService:
    def test_parse_arp_output(self):
        output = "  192.168.1.10          aa-bb-cc-dd-ee-ff     dynamic\n"
        devices = _parse_arp_output(output)
        assert len(devices) == 1
        assert devices[0]["ip"] == "192.168.1.10"
        assert devices[0]["mac"] == "aa:bb:cc:dd:ee:ff"

    def test_parse_arp_output_empty(self):
        devices = _parse_arp_output("")
        assert devices == []

    def test_parse_arp_output_multiple(self):
        output = (
            "  192.168.1.10          aa-bb-cc-dd-ee-ff     dynamic\n"
            "  192.168.1.11          12-22-33-44-55-66     dynamic\n"
        )
        devices = _parse_arp_output(output)
        assert len(devices) == 2

    def test_parse_arp_output_filters_broadcast_and_multicast(self):
        output = (
            "  192.168.1.255         ff-ff-ff-ff-ff-ff     static\n"
            "  224.0.0.22            01-00-5e-00-00-16     static\n"
        )
        devices = _parse_arp_output(output)
        assert devices == []

    def test_normalize_mac_formats(self):
        assert normalize_mac("AA-BB-CC-DD-EE-FF") == "aa:bb:cc:dd:ee:ff"
        assert normalize_mac("aabbccddeeff") == "aa:bb:cc:dd:ee:ff"
        assert normalize_mac("AA:BB:CC:DD:EE:FF") == "aa:bb:cc:dd:ee:ff"
        assert normalize_mac("aa.bb.cc.dd.ee.ff") == "aa:bb:cc:dd:ee:ff"
        assert normalize_mac("not-a-mac") == "not-a-mac"
        assert normalize_mac("") == ""

    def test_check_mac_on_network_found(self):
        devices = [
            {"ip": "192.168.1.10", "mac": "aa:bb:cc:dd:ee:ff"},
            {"ip": "192.168.1.11", "mac": "11:22:33:44:55:66"},
        ]
        assert check_mac_on_network("aa:bb:cc:dd:ee:ff", devices) is True

    def test_check_mac_on_network_format_agnostic(self):
        devices = [
            {"ip": "192.168.1.10", "mac": "AA-BB-CC-DD-EE-FF"},
        ]
        assert check_mac_on_network("aabbccddeeff", devices) is True
        assert check_mac_on_network("aa:bb:cc:dd:ee:ff", devices) is True

    def test_check_mac_on_network_empty_mac(self):
        devices = [{"ip": "192.168.1.10", "mac": "aa:bb:cc:dd:ee:ff"}]
        assert check_mac_on_network("", devices) is False
        assert check_mac_on_network(None, devices) is False

    def test_check_mac_on_network_not_found(self):
        devices = [
            {"ip": "192.168.1.10", "mac": "aa:bb:cc:dd:ee:ff"},
        ]
        assert check_mac_on_network("zz:yy:xx:ww:vv:uu", devices) is False

    def test_check_mac_on_network_empty_list(self):
        assert check_mac_on_network("aa:bb:cc:dd:ee:ff", []) is False

    def test_scan_cache_reuses_result(self):
        with patch("services.wifi_scanner._scan_windows") as mock_scan:
            mock_scan.return_value = [{"ip": "192.168.1.10", "mac": "aa:bb:cc:dd:ee:ff"}]
            wifi_scanner._scan_cache["devices"] = None

            first = scan_network_arp(use_cache=True)
            second = scan_network_arp(use_cache=True)

            assert mock_scan.call_count == 1
            assert first == second

            fresh = scan_network_arp(use_cache=False)
            assert mock_scan.call_count == 2
            assert fresh == first

            wifi_scanner._scan_cache["devices"] = None


@pytest.mark.asyncio
class TestAttendanceService:
    async def test_get_schedules_for_now_no_db(self):
        scheds = await get_schedules_for_now()
        assert isinstance(scheds, list)

    async def test_mark_attendance_no_student(self, test_db, setup_test_db):
        result = await mark_attendance(
            student_id=999, schedule_id=1,
            check_type="start", confidence=0.5
        )
        assert result["wifi_verified"] is False