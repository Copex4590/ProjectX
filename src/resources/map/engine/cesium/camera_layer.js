/**
 * SAVE-108 — Cesium camera layer.
 */
(function(global)
{
    "use strict";

    function createCameraLayer(viewer, Cesium)
    {
        const WORLD_VIEW_CENTER = { lon: 0.0, lat: 20.0 };
        const WORLD_VIEW_HEIGHT_M = 18000000.0;
        const FOCUS_SHIP_HEIGHT_M = 2500.0;
        const FOCUS_POINT_HEIGHT_M = 250000.0;
        const DEFAULT_FLY_DURATION_S = 0.75;
        const SMOOTH_FLY_DURATION_S = 1.0;

        function flyToOptions(destination, duration)
        {
            return {
                destination: destination,
                duration: duration,
                easingFunction: Cesium.EasingFunction.QUADRATIC_IN_OUT
            };
        }

        function resetWorldView()
        {
            viewer.camera.setView({
                destination: Cesium.Cartesian3.fromDegrees(
                    WORLD_VIEW_CENTER.lon,
                    WORLD_VIEW_CENTER.lat,
                    WORLD_VIEW_HEIGHT_M
                ),
                orientation: {
                    heading: 0.0,
                    pitch: Cesium.Math.toRadians(-90.0),
                    roll: 0.0
                }
            });
        }

        function flyToDegrees(lon, lat, heightM, duration)
        {
            viewer.camera.flyTo(flyToOptions(
                Cesium.Cartesian3.fromDegrees(lon, lat, heightM),
                duration
            ));
        }

        function flyToCartesian(position, heightM, duration)
        {
            const cartographic = Cesium.Cartographic.fromCartesian(position);

            flyToDegrees(
                Cesium.Math.toDegrees(cartographic.longitude),
                Cesium.Math.toDegrees(cartographic.latitude),
                heightM,
                duration
            );
        }

        function flyToShip(position)
        {
            flyToCartesian(position, FOCUS_SHIP_HEIGHT_M, DEFAULT_FLY_DURATION_S);
        }

        function flyToPoint(point)
        {
            flyToDegrees(
                point.lon,
                point.lat,
                FOCUS_POINT_HEIGHT_M,
                SMOOTH_FLY_DURATION_S
            );
        }

        function flyToEntity(entity)
        {
            if (!entity)
                return;

            viewer.flyTo(entity, {
                duration: SMOOTH_FLY_DURATION_S,
                easingFunction: Cesium.EasingFunction.QUADRATIC_IN_OUT
            });
        }

        function focusObservationPoints(points, coverageLayer)
        {
            if (!points.length)
            {
                resetWorldView();
                return;
            }

            const referencePoint = points.find(point => point.reference) || points[0];

            if (!referencePoint)
                return;

            if (referencePoint.reference && coverageLayer)
            {
                const coverageEntity = coverageLayer.getEntity(referencePoint.id);

                if (coverageEntity)
                {
                    flyToEntity(coverageEntity);
                    return;
                }
            }

            flyToPoint(referencePoint);
        }

        return {
            resetWorldView: resetWorldView,
            flyToShip: flyToShip,
            flyToPoint: flyToPoint,
            flyToEntity: flyToEntity,
            focusObservationPoints: focusObservationPoints,
            initialize: function() {},
            activate: function() {},
            suspend: function() {},
            resume: function() {},
            shutdown: function() {}
        };
    }

    global.createCameraLayer = createCameraLayer;
})(window);
