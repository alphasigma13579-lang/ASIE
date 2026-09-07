from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"


class LiveMarketCockpitContractTests(unittest.TestCase):
    def setUp(self) -> None:
        self.cockpit = (SRC / "LiveCockpit.tsx").read_text(encoding="utf-8")
        self.map = (SRC / "LiveMarketMap.tsx").read_text(encoding="utf-8")
        self.api = (SRC / "api.ts").read_text(encoding="utf-8")
        self.workspace = (SRC / "LiveIntelligenceWorkspace.tsx").read_text(encoding="utf-8")
        self.vite_types = (SRC / "vite-env.d.ts").read_text(encoding="utf-8")
        self.language = (SRC / "customerLanguage.tsx").read_text(encoding="utf-8")

    def test_cockpit_replaces_static_competitors_with_the_provider_boundary(self) -> None:
        self.assertIn('import { LiveMarketMap } from "./LiveMarketMap";', self.cockpit)
        self.assertIn("<LiveMarketMap", self.cockpit)
        self.assertIn("projectId?: string", self.cockpit)
        self.assertNotIn("منشأة مماثلة", self.cockpit)
        self.assertNotIn("local-map--demo", self.cockpit)

    def test_customer_context_is_projected_without_changing_the_search_query(self) -> None:
        self.assertIn("customerBusinessText(primarySectorId, locale)", self.cockpit)
        self.assertIn("customerLocationLabel(part, locale)", self.cockpit)
        self.assertIn("sectorLabel={customerSector}", self.cockpit)
        self.assertIn("sectorLabel?: string", self.map)
        self.assertIn("query: sector", self.map)
        self.assertIn("sectorLabel || text", self.map)

    def test_governed_sector_ids_have_bilingual_customer_labels(self) -> None:
        expected_labels = {
            "sec_05": ("الصناعة والتصنيع", "Manufacturing"),
            "sec_07": ("العقارات", "Real estate"),
            "sec_08": ("اللوجستيات وسلاسل الإمداد", "Logistics and supply chain"),
            "sec_09": ("السياحة والترفيه", "Tourism and entertainment"),
            "sec_11": ("التقنية والابتكار", "Technology and innovation"),
            "sec_12": ("القطاع المالي", "Financial services"),
            "sec_14": ("الصحة والطب", "Healthcare"),
            "sec_17": ("الأغذية والزراعة والأمن الغذائي", "Agriculture, food, and food security"),
        }
        for sector_id, (arabic, english) in expected_labels.items():
            with self.subTest(sector_id=sector_id):
                self.assertIn(
                    f'{sector_id}: {{ ar: "{arabic}", en: "{english}" }}',
                    self.language,
                )

    def test_market_request_requires_confirmed_project_location_and_sector(self) -> None:
        self.assertIn("projectId && sector?.trim() && hasConfirmedLocation", self.map)
        self.assertIn("البحث عن منافسين قرب الموقع", self.map)
        self.assertIn("reverseGeocode", self.map)
        self.assertIn("searchMarketCompetitors", self.map)
        self.assertIn("لن تُعرض بيانات بديلة", self.map)

    def test_browser_map_never_receives_the_server_key_or_loads_on_mount(self) -> None:
        self.assertIn("VITE_GOOGLE_MAPS_BROWSER_KEY", self.map)
        self.assertIn('VITE_ASIE_LIVE_BROWSER_MAPS_ENABLED === "true"', self.map)
        self.assertIn('state !== "ready"', self.map)
        self.assertNotIn("GOOGLE_MAPS_API_KEY", self.map)
        self.assertNotIn("localStorage", self.map)
        self.assertIn("VITE_GOOGLE_MAPS_BROWSER_KEY", self.vite_types)
        self.assertIn("VITE_ASIE_LIVE_BROWSER_MAPS_ENABLED", self.vite_types)

    def test_api_contract_keeps_the_location_and_market_boundaries_explicit(self) -> None:
        self.assertIn('"/api/v1/location/reverse-geocode"', self.api)
        self.assertIn('"/api/v1/market/competitors/search"', self.api)
        self.assertIn("device_location_persisted: false", self.api)
        self.assertIn("eligible_for_pinecone: false", self.api)
        self.assertIn("finance_mutated: false", self.api)
        self.assertIn("snapshot_mutated: false", self.api)

    def test_live_research_is_mounted_without_exposing_provider_diagnostics(self) -> None:
        self.assertIn("buildLiveMarketContext", self.cockpit)
        self.assertIn("<LiveIntelligenceWorkspace", self.cockpit)
        self.assertIn("locationReady={liveResearchReady}", self.cockpit)
        self.assertIn("أكّد موقع المشروع أولًا", self.workspace)
        self.assertIn('"/api/v1/intelligence/market-context"', self.api)
        self.assertNotIn("DeepSeek", self.workspace)
        self.assertNotIn("Tavily", self.workspace)
        self.assertNotIn("Pinecone", self.workspace)
        self.assertNotIn("Google Maps", self.workspace)
        self.assertNotIn("failure.provider", self.workspace)

    def test_live_research_resets_with_project_context_and_never_claims_unsaved_retry_data(self) -> None:
        self.assertIn('useEffect', self.cockpit)
        self.assertIn('contextRevisionRef', self.cockpit)
        self.assertIn('primarySectorId', self.cockpit)
        self.assertNotIn("حُفظت مدخلاتك", self.workspace)
        self.assertNotIn("حُفظت مدخلاتك", self.map)
        self.assertNotIn("Your inputs are preserved", self.workspace)
        self.assertNotIn("Your inputs are preserved", self.map)


if __name__ == "__main__":
    unittest.main()
