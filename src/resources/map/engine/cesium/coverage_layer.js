/**
 * SAVE-108 — Cesium coverage layer (geodesic reference circles).
 */
(function(global)
{
    "use strict";

    function createCoverageLayer(viewer, Cesium)
    {
        const coverages = {};
        let visible = true;

        function setVisible(enabled)
        {
            visible = !!enabled;

            for (const pointId in coverages)
                coverages[pointId].entity.show = visible;

            viewer.scene.requestRender();
        }

        function isVisible()
        {
            return visible;
        }

        function removeCoverage(pointId)
        {
            const key = String(pointId);
            const record = coverages[key];

            if (!record)
                return;

            viewer.entities.remove(record.entity);
            delete coverages[key];
        }

        function clear()
        {
            for (const pointId in coverages)
                removeCoverage(pointId);
        }

        function addCoverage(point)
        {
            const pointId = String(point.id);
            const radiusMeters = global.CesiumGeodesic.coverageRadiusMeters(point);
            const style = global.CesiumGeodesic.createCoverageStyle(Cesium);

            const entity = viewer.entities.add({
                id: "coverage-" + pointId,
                position: Cesium.Cartesian3.fromDegrees(point.lon, point.lat),
                show: visible,
                ellipse: {
                    semiMajorAxis: radiusMeters,
                    semiMinorAxis: radiusMeters,
                    material: style.material,
                    outline: true,
                    outlineColor: style.outlineColor,
                    outlineWidth: style.outlineWidth,
                    height: 0.0,
                    heightReference: Cesium.HeightReference.CLAMP_TO_GROUND
                }
            });

            coverages[pointId] = { entity: entity, point: point };
        }

        function updateCoverage(point)
        {
            if (!global.CesiumGeodesic.shouldRenderCoverage(point))
            {
                removeCoverage(point.id);
                return;
            }

            const pointId = String(point.id);
            const record = coverages[pointId];

            if (!record)
            {
                addCoverage(point);
                return;
            }

            const radiusMeters = global.CesiumGeodesic.coverageRadiusMeters(point);
            const style = global.CesiumGeodesic.createCoverageStyle(Cesium);

            record.point = point;
            record.entity.position = Cesium.Cartesian3.fromDegrees(point.lon, point.lat);
            record.entity.show = visible;
            record.entity.ellipse = new Cesium.EllipseGraphics({
                semiMajorAxis: radiusMeters,
                semiMinorAxis: radiusMeters,
                material: style.material,
                outline: true,
                outlineColor: style.outlineColor,
                outlineWidth: style.outlineWidth,
                height: 0.0,
                heightReference: Cesium.HeightReference.CLAMP_TO_GROUND
            });
        }

        function sync(points)
        {
            const activeIds = new Set();

            for (const point of points)
            {
                if (!global.CesiumGeodesic.shouldRenderCoverage(point))
                    continue;

                const pointId = String(point.id);
                activeIds.add(pointId);
                updateCoverage(point);
            }

            for (const pointId in coverages)
            {
                if (!activeIds.has(pointId))
                    removeCoverage(pointId);
            }
        }

        function getEntity(pointId)
        {
            const record = coverages[String(pointId)];
            return record ? record.entity : null;
        }

        return {
            setVisible: setVisible,
            isVisible: isVisible,
            addCoverage: addCoverage,
            updateCoverage: updateCoverage,
            removeCoverage: removeCoverage,
            clear: clear,
            sync: sync,
            getEntity: getEntity,
            count: function()
            {
                return Object.keys(coverages).length;
            },
            initialize: function() {},
            activate: function()
            {
                setVisible(true);
            },
            suspend: function()
            {
                setVisible(false);
            },
            resume: function()
            {
                setVisible(true);
            },
            shutdown: function()
            {
                clear();
            }
        };
    }

    global.createCoverageLayer = createCoverageLayer;
})(window);
