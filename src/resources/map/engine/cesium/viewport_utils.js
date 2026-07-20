/**
 * SAVE-108 — Shared Cesium viewport helpers for performance optimizations.
 */
(function(global)
{
    "use strict";

    function viewRectangle(viewer, Cesium)
    {
        const rectangle = viewer.camera.computeViewRectangle(viewer.scene.globe.ellipsoid);

        if (!rectangle)
            return null;

        return {
            west: Cesium.Math.toDegrees(rectangle.west),
            south: Cesium.Math.toDegrees(rectangle.south),
            east: Cesium.Math.toDegrees(rectangle.east),
            north: Cesium.Math.toDegrees(rectangle.north)
        };
    }

    function isPointInRectangle(lon, lat, rectangle)
    {
        if (!rectangle)
            return true;

        if (lat < rectangle.south || lat > rectangle.north)
            return false;

        if (rectangle.west <= rectangle.east)
            return lon >= rectangle.west && lon <= rectangle.east;

        return lon >= rectangle.west || lon <= rectangle.east;
    }

    function isPointInView(viewer, Cesium, lon, lat)
    {
        return isPointInRectangle(lon, lat, viewRectangle(viewer, Cesium));
    }

    function distanceDisplayCondition(Cesium, cameraHeightM)
    {
        if (cameraHeightM > 12000000.0)
            return new Cesium.DistanceDisplayCondition(0.0, 2500000.0);

        if (cameraHeightM > 3000000.0)
            return new Cesium.DistanceDisplayCondition(0.0, 8000000.0);

        return undefined;
    }

    global.CesiumViewport = {
        viewRectangle: viewRectangle,
        isPointInView: isPointInView,
        distanceDisplayCondition: distanceDisplayCondition
    };
})(window);
