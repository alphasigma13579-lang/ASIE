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

    def test_cockpit_replaces_static_competitors_with_the_provider_boundary(self) -> None:
        self.assertIn('import { LiveMarketMap } from "./LiveMarketMap";', self.cockpit)
        self.assertIn("<LiveMarketMap", self.cockpit)
        self.assertIn("projectId?: string", self.cockpit)
        self.assertNotIn("منشأة مماثلة", self.cockpit)
        self.assertNotIn("local-map--demo", self.cockpit)

    def test_market_request_requires_confirmed_project_location_and_sector(self) -> None:
        self.assertIn("projectId && sector?.trim() && hasConfirmedLocation", self.map)
        self.assertIn("تحديث المنافسين للموقع المؤكد", self.map)
        self.assertIn("reverseGeocode", self.map)
        self.assertIn("searchMarketCompetitors", self.map)
        self.assertIn('لا توجد بيانات بديلة أو تجريبية هنا', self.map)

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


if __name__ == "__main__":
    unittest.main()
