/**
 * SAVE-108 — Cesium observation marker layer.
 */
(function(global)
{
    "use strict";

    function createObservationLayer(viewer, Cesium)
    {
        const markers = {};

        function observationColor(active)
        {
            return active
                ? Cesium.Color.fromCssColorString("#43a047")
                : Cesium.Color.fromCssColorString("#e53935");
        }

        function removePoint(pointId)
        {
            const key = String(pointId);
            const entity = markers[key];

            if (!entity)
                return;

            viewer.entities.remove(entity);
            delete markers[key];
        }

        function clear()
        {
            for (const pointId in markers)
                removePoint(pointId);
        }

        function addPoint(point)
        {
            const pointId = String(point.id);

            markers[pointId] = viewer.entities.add({
                id: "observation-" + pointId,
                position: Cesium.Cartesian3.fromDegrees(point.lon, point.lat),
                point: {
                    pixelSize: 14,
                    color: observationColor(!!point.active),
                    outlineColor: Cesium.Color.WHITE,
                    outlineWidth: 2,
                    disableDepthTestDistance: Number.POSITIVE_INFINITY
                }
            });
        }

        function updatePoint(point)
        {
            const pointId = String(point.id);
            let entity = markers[pointId];

            if (!entity)
            {
                addPoint(point);
                return;
            }

            entity.position = Cesium.Cartesian3.fromDegrees(point.lon, point.lat);
            entity.point = new Cesium.PointGraphics({
                pixelSize: 14,
                color: observationColor(!!point.active),
                outlineColor: Cesium.Color.WHITE,
                outlineWidth: 2,
                disableDepthTestDistance: Number.POSITIVE_INFINITY
            });
        }

        function sync(points)
        {
            layer.lastSyncedPoints = points.slice();
            const activeIds = new Set();

            for (const point of points)
            {
                const pointId = String(point.id);
                activeIds.add(pointId);
                updatePoint(point);
            }

            for (const pointId in markers)
            {
                if (!activeIds.has(pointId))
                    removePoint(pointId);
            }
        }

        const layer = {
            lastSyncedPoints: [],
            addPoint: addPoint,
            updatePoint: updatePoint,
            removePoint: removePoint,
            clear: clear,
            sync: sync,
            getEntity: function(pointId)
            {
                return markers[String(pointId)] || null;
            },
            count: function()
            {
                return Object.keys(markers).length;
            },
            initialize: function() {},
            activate: function() {},
            suspend: function() {},
            resume: function() {},
            shutdown: function()
            {
                clear();
            }
        };

        return layer;
    }

    global.createObservationLayer = createObservationLayer;
})(window);
