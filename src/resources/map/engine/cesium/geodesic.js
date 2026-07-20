/**
 * SAVE-108 — Geodesic helpers for Cesium coverage rendering.
 *
 * Visual geometry only. GeoContext remains authoritative in Python.
 */
(function(global)
{
    "use strict";

    function coverageRadiusMeters(point)
    {
        const radiusKm = Number(point.coverage_radius_km);
        return Number.isFinite(radiusKm) && radiusKm > 0
            ? radiusKm * 1000.0
            : 0.0;
    }

    function shouldRenderCoverage(point)
    {
        if (point.coverage_visible === false)
            return false;

        return !!point.reference && coverageRadiusMeters(point) > 0.0;
    }

    function primaryMapColor()
    {
        const value = getComputedStyle(document.documentElement)
            .getPropertyValue("--px-primary-500")
            .trim();

        return value || "#1e88e5";
    }

    function createCoverageStyle(Cesium)
    {
        const color = Cesium.Color.fromCssColorString(primaryMapColor());

        return {
            material: color.withAlpha(0.08),
            outlineColor: color,
            outlineWidth: 1.5
        };
    }

    const EARTH_RADIUS_KM = 6371.0;

    function bearingBetween(lat1, lon1, lat2, lon2)
    {
        const lat1Rad = lat1 * Math.PI / 180.0;
        const lat2Rad = lat2 * Math.PI / 180.0;
        const dLon = (lon2 - lon1) * Math.PI / 180.0;

        const y = Math.sin(dLon) * Math.cos(lat2Rad);
        const x = Math.cos(lat1Rad) * Math.sin(lat2Rad)
            - Math.sin(lat1Rad) * Math.cos(lat2Rad) * Math.cos(dLon);

        return (Math.atan2(y, x) * 180.0 / Math.PI + 360.0) % 360.0;
    }

    function destinationPoint(lat, lon, bearingDeg, distanceKm)
    {
        const bearingRad = bearingDeg * Math.PI / 180.0;
        const lat1 = lat * Math.PI / 180.0;
        const lon1 = lon * Math.PI / 180.0;
        const angularDistance = distanceKm / EARTH_RADIUS_KM;

        const lat2 = Math.asin(
            Math.sin(lat1) * Math.cos(angularDistance)
            + Math.cos(lat1) * Math.sin(angularDistance) * Math.cos(bearingRad)
        );
        const lon2 = lon1 + Math.atan2(
            Math.sin(bearingRad) * Math.sin(angularDistance) * Math.cos(lat1),
            Math.cos(angularDistance) - Math.sin(lat1) * Math.sin(lat2)
        );

        return {
            lat: lat2 * 180.0 / Math.PI,
            lon: ((lon2 * 180.0 / Math.PI + 540.0) % 360.0) - 180.0
        };
    }

    global.CesiumGeodesic = {
        coverageRadiusMeters: coverageRadiusMeters,
        shouldRenderCoverage: shouldRenderCoverage,
        createCoverageStyle: createCoverageStyle,
        bearingBetween: bearingBetween,
        destinationPoint: destinationPoint,
        EARTH_RADIUS_KM: EARTH_RADIUS_KM
    };
})(window);
