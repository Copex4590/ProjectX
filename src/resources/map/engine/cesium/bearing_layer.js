/**
 * SAVE-108 — Reference bearing visualization layer.
 */
(function(global)
{
    "use strict";

    const BEARING_COLOR = "#90caf9";

    function createBearingLayer(viewer, Cesium)
    {
        const bearings = {};
        let referencePoint = null;
        let visible = true;

        function setVisible(enabled)
        {
            visible = !!enabled;

            for (const mmsi in bearings)
                bearings[mmsi].entity.show = visible;

            viewer.scene.requestRender();
        }

        function setReferencePoint(point)
        {
            referencePoint = point;
        }

        function removeBearing(mmsi)
        {
            const key = String(mmsi);
            const record = bearings[key];

            if (!record)
                return;

            viewer.entities.remove(record.entity);
            delete bearings[key];
        }

        function clear()
        {
            for (const mmsi in bearings)
                removeBearing(mmsi);
        }

        function updateBearing(ship)
        {
            const mmsi = String(ship.mmsi);
            const bearing = Number(ship.reference_bearing_deg);

            if (
                !referencePoint
                || !Number.isFinite(bearing)
                || ship.lat === undefined
                || ship.lon === undefined
            )
            {
                removeBearing(mmsi);
                return;
            }

            if (
                Object.keys(bearings).length > 150
                && !global.CesiumViewport.isPointInView(
                    viewer,
                    Cesium,
                    Number(ship.lon),
                    Number(ship.lat)
                )
            )
            {
                if (bearings[mmsi])
                    bearings[mmsi].entity.show = false;

                return;
            }

            const positions = Cesium.Cartesian3.fromDegreesArray([
                referencePoint.lon,
                referencePoint.lat,
                ship.lon,
                ship.lat
            ]);

            let record = bearings[mmsi];

            if (!record)
            {
                record = {
                    entity: viewer.entities.add({
                        id: "bearing-" + mmsi,
                        show: visible,
                        polyline: {
                            positions: positions,
                            width: 1,
                            material: Cesium.Color.fromCssColorString(BEARING_COLOR).withAlpha(0.65),
                            clampToGround: true
                        }
                    })
                };
                bearings[mmsi] = record;
                return;
            }

            record.entity.show = visible;
            record.entity.polyline.positions = new Cesium.ConstantProperty(positions);
        }

        function sync(ships)
        {
            const active = new Set();

            for (const ship of ships)
            {
                active.add(String(ship.mmsi));
                updateBearing(ship);
            }

            for (const mmsi in bearings)
            {
                if (!active.has(mmsi))
                    removeBearing(mmsi);
            }
        }

        return {
            setVisible: setVisible,
            setReferencePoint: setReferencePoint,
            updateBearing: updateBearing,
            removeBearing: removeBearing,
            clear: clear,
            sync: sync,
            count: function()
            {
                return Object.keys(bearings).length;
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

    global.createBearingLayer = createBearingLayer;
})(window);
