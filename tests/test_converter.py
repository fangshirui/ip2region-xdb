import os
import tempfile
import unittest

from ip2region_xdb.converter import IPRecord, MMDBConverter


class ParseGeoLiteRecordTest(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        with open(
            os.path.join(self.temp_dir.name, "countries.txt"),
            "w",
            encoding="utf-8",
        ) as f:
            f.write("US,美国\nTR,土尔其\nHK,香港(中国)\n")
        with open(
            os.path.join(self.temp_dir.name, "us_states.txt"),
            "w",
            encoding="utf-8",
        ) as f:
            f.write("俄勒冈州,Oregon\n")
        self.converter = MMDBConverter(
            "city.mmdb",
            "country.mmdb",
            "asn.mmdb",
            data_dir=self.temp_dir.name,
        )

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_country_name_uses_iso_code_mapping(self):
        data = {
            "country": {
                "iso_code": "TR",
                "names": {"zh-CN": "土耳其", "en": "Türkiye"},
            },
        }

        parsed = self.converter._parse_city_record(data)
        self.assertEqual("土尔其", parsed["country"])
        self.assertEqual("TR", parsed["country_iso"])
        self.assertEqual(("", "土尔其", "TR"), self.converter._parse_country_record(data))

    def test_unconfigured_country_falls_back_to_geolite_name(self):
        data = {
            "country": {
                "iso_code": "BQ",
                "names": {
                    "zh-CN": "博奈尔岛、圣尤斯达蒂斯和萨巴",
                    "en": "Bonaire, Sint Eustatius and Saba",
                },
            },
        }

        parsed = self.converter._parse_city_record(data)
        self.assertEqual("博奈尔岛、圣尤斯达蒂斯和萨巴", parsed["country"])
        self.assertEqual("BQ", parsed["country_iso"])

    def test_us_state_uses_configured_chinese_name(self):
        data = {
            "country": {
                "iso_code": "US",
                "names": {"zh-CN": "美国", "en": "United States"},
            },
            "subdivisions": [{
                "iso_code": "OR",
                "names": {"zh-CN": "GeoLite中文名", "en": "Oregon"},
            }],
        }

        parsed = self.converter._parse_city_record(data)
        self.assertEqual("美国", parsed["country"])
        self.assertEqual("俄勒冈州", parsed["province"])
        self.assertEqual("US", parsed["country_iso"])

    def test_geocn_country_iso_is_cn(self):
        parsed = self.converter._parse_geocn_record({"province": "福建省"})
        self.assertEqual("中国", parsed["country"])
        self.assertEqual("CN", parsed["country_iso"])

    def test_source_line_appends_country_iso(self):
        record = IPRecord(
            start_ip=16777472,
            end_ip=16778239,
            continent="亚洲",
            country="中国",
            province="福建省",
            city="福州市",
            isp="电信",
            country_iso="CN",
        )

        self.assertEqual(
            "1.0.1.0|1.0.3.255|亚洲|中国|福建省|福州市||电信||CN",
            record.to_line(),
        )

    def test_ranges_with_different_country_iso_do_not_merge(self):
        records = [
            IPRecord(0, 9, country="示例国家", country_iso="AA", priority=1),
            IPRecord(10, 19, country="示例国家", country_iso="BB", priority=1),
        ]

        normalized = self.converter._normalize_ranges(records, is_ipv6=False)

        self.assertEqual(2, len(normalized))
        self.assertEqual((0, 9, "AA"), (
            normalized[0].start_ip,
            normalized[0].end_ip,
            normalized[0].country_iso,
        ))
        self.assertEqual((10, 19, "BB"), (
            normalized[1].start_ip,
            normalized[1].end_ip,
            normalized[1].country_iso,
        ))


if __name__ == "__main__":
    unittest.main()
