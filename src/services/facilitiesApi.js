import { state } from "./mockState.js";
import { getApiBaseUrl, getApiMode } from "../config.js";

export const facilitiesApi = {
  async getFacilities(filter = {}) {
    if (getApiMode() === "live") {
      try {
        const query = new URLSearchParams(filter).toString();
        const res = await fetch(`${getApiBaseUrl()}/infrastructure${query ? `?${query}` : ""}`);
        if (res.ok) {
          const data = await res.json();
          if (data.facilities && data.facilities.length) {
            return data.facilities;
          }
        }
      } catch (err) {
        console.warn("Live infrastructure API fallback to local state:", err);
      }
    }
    let list = state.facilities;
    if (filter.district) {
      list = list.filter((f) => f.district.toLowerCase() === filter.district.toLowerCase());
    }
    if (filter.type) {
      list = list.filter((f) => f.type.toLowerCase() === filter.type.toLowerCase());
    }
    if (filter.status) {
      list = list.filter((f) => f.officialStatus.toLowerCase() === filter.status.toLowerCase());
    }
    return list;
  },

  async getFacilityById(id) {
    return state.facilities.find((f) => f.id === id) || null;
  },

  async updateFacilityStatus(id, newStatus) {
    const fac = state.facilities.find((f) => f.id === id);
    if (fac) {
      fac.officialStatus = newStatus;
      if (newStatus === "OPERATIONAL") fac.abandonmentScore = 15;
      if (newStatus === "ABANDONED") fac.abandonmentScore = 95;
    }
    return fac;
  },

  /**
   * Fetches real-world live civic facilities from OpenStreetMap Overpass API
   * for any state or current viewport in India.
   */
  async fetchLiveOsmFacilities(bbox = null, regionName = "India") {
    try {
      // Default to Delhi NCR / Central India if no bbox provided
      const [south, west, north, east] = Array.isArray(bbox) && bbox.length === 4
        ? bbox
        : [28.45, 76.95, 28.85, 77.35];

      const overpassQuery = `[out:json][timeout:15];(
        node["amenity"="toilets"](${south},${west},${north},${east});
        node["amenity"="drinking_water"](${south},${west},${north},${east});
        node["amenity"="school"](${south},${west},${north},${east});
        node["amenity"="clinic"](${south},${west},${north},${east});
        node["amenity"="hospital"](${south},${west},${north},${east});
      );out 40;`;

      const res = await fetch("https://overpass-api.de/api/interpreter", {
        method: "POST",
        body: overpassQuery,
      });

      if (!res.ok) throw new Error(`Overpass API error: ${res.status}`);
      const data = await res.json();
      if (!data.elements || !data.elements.length) return [];

      const newLiveFacilities = data.elements
        .filter((el) => el.lat && el.lon)
        .map((el) => {
          const amenity = el.tags?.amenity || "facility";
          let type = "community";
          if (amenity === "toilets") type = "toilet";
          else if (amenity === "drinking_water") type = "water";
          else if (amenity === "school") type = "school";
          else if (amenity === "hospital" || amenity === "clinic") type = "health";

          const name = el.tags?.name || `Public ${type.charAt(0).toUpperCase() + type.slice(1)} (OSM #${el.id})`;
          const district = el.tags?.["addr:district"] || el.tags?.["addr:city"] || regionName || "India";

          return {
            id: `osm-${el.id}`,
            name,
            type,
            district,
            state: el.tags?.["addr:state"] || regionName,
            lat: el.lat,
            lng: el.lon,
            officialStatus: "OPERATIONAL",
            abandonmentScore: 10,
            populationCatchment: 8500,
            establishedYear: 2020,
            lastInspection: "Live OSM Feed",
            conditionNotes: `Live geographic asset from OpenStreetMap (${district}). Amenity: ${amenity}`,
            citizenReportCount: 0,
            recommendedAction: "MAINTAIN",
          };
        });

      // Merge into state avoiding duplicates
      newLiveFacilities.forEach((item) => {
        if (!state.facilities.some((f) => f.id === item.id)) {
          state.facilities.push(item);
        }
      });

      return newLiveFacilities;
    } catch (err) {
      console.warn("Live OSM Overpass fetch fallback:", err);
      return [];
    }
  },
};

