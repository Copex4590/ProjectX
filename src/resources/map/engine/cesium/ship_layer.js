/**
 * SAVE-108 — Cesium ship and trail layer.
 */
(function(global)
{
    "use strict";

    const MOVING_THRESHOLD_KN = 0.5;
    const TRAIL_POINT_LIMIT = 50;
    const HEADING_VECTOR_KM = 2.0;
    const LARGE_FLEET_THRESHOLD = 150;

    function createShipLayer(viewer, Cesium)
    {
        const ships = {};
        const shipPayloads = {};
        const entityPool = global.createEntityPool();

        function shipSpeedKn(ship)
        {
            const speed = Number(ship.speed);
            return Number.isFinite(speed) ? speed : 0;
        }

        function shipCourseDeg(ship)
        {
            const course = Number(ship.course);

            if (Number.isFinite(course))
                return ((course % 360) + 360) % 360;

            const heading = Number(ship.heading);

            if (Number.isFinite(heading))
                return ((heading % 360) + 360) % 360;

            return 0;
        }

        function isShipMoving(ship)
        {
            return shipSpeedKn(ship) >= MOVING_THRESHOLD_KN;
        }

        function styleKey(ship)
        {
            if (isShipMoving(ship))
                return "moving:" + shipCourseDeg(ship);

            return "stationary";
        }

        function shipMarkerStyle(ship)
        {
            if (isShipMoving(ship))
            {
                return {
                    label: {
                        text: "▲",
                        font: "20px sans-serif",
                        fillColor: Cesium.Color.fromCssColorString("#1e88e5"),
                        style: Cesium.LabelStyle.FILL,
                        verticalOrigin: Cesium.VerticalOrigin.CENTER,
                        horizontalOrigin: Cesium.HorizontalOrigin.CENTER,
                        rotation: Cesium.Math.toRadians(shipCourseDeg(ship)),
                        disableDepthTestDistance: Number.POSITIVE_INFINITY
                    },
                    point: undefined
                };
            }

            return {
                label: undefined,
                point: {
                    pixelSize: 10,
                    color: Cesium.Color.fromCssColorString("#1e88e5"),
                    outlineColor: Cesium.Color.WHITE,
                    outlineWidth: 1,
                    disableDepthTestDistance: Number.POSITIVE_INFINITY
                }
            };
        }

        function headingVectorPositions(ship)
        {
            const heading = shipCourseDeg(ship);
            const tip = global.CesiumGeodesic.destinationPoint(
                Number(ship.lat),
                Number(ship.lon),
                heading,
                HEADING_VECTOR_KM
            );

            return [
                ship.lon,
                ship.lat,
                tip.lon,
                tip.lat
            ];
        }

        function applyDistanceDisplay(record)
        {
            const cameraHeight = viewer.camera.positionCartographic.height;
            const condition = global.CesiumViewport.distanceDisplayCondition(
                Cesium,
                cameraHeight
            );

            if (condition)
                record.entity.distanceDisplayCondition = condition;
            else if (record.entity.distanceDisplayCondition)
                record.entity.distanceDisplayCondition = undefined;
        }

        function shouldUpdateShipDetail(ship)
        {
            if (Object.keys(ships).length <= LARGE_FLEET_THRESHOLD)
                return true;

            return global.CesiumViewport.isPointInView(
                viewer,
                Cesium,
                Number(ship.lon),
                Number(ship.lat)
            );
        }

        function updateHeadingVector(record, ship, Cesium)
        {
            if (!shouldUpdateShipDetail(ship))
            {
                if (record.headingEntity)
                    record.headingEntity.show = false;

                return;
            }

            if (!isShipMoving(ship))
            {
                if (record.headingEntity)
                {
                    record.headingEntity.show = false;
                }

                return;
            }

            const positions = Cesium.Cartesian3.fromDegreesArray(
                headingVectorPositions(ship)
            );

            if (!record.headingEntity)
            {
                record.headingEntity = viewer.entities.add({
                    id: "heading-" + String(ship.mmsi),
                    polyline: {
                        positions: positions,
                        width: 2,
                        material: Cesium.Color.fromCssColorString("#1e88e5").withAlpha(0.85),
                        clampToGround: true
                    }
                });
                return;
            }

            record.headingEntity.show = true;
            record.headingEntity.polyline.positions = new Cesium.ConstantProperty(
                positions
            );
        }

        function applyShipStyle(record, ship)
        {
            const nextStyleKey = styleKey(ship);

            if (record.lastStyleKey === nextStyleKey)
                return;

            record.lastStyleKey = nextStyleKey;
            const style = shipMarkerStyle(ship);

            if (style.label)
            {
                record.entity.label = new Cesium.LabelGraphics(style.label);
                record.entity.point = undefined;
            }
            else if (style.point)
            {
                record.entity.point = new Cesium.PointGraphics(style.point);
                record.entity.label = undefined;
            }
        }

        function createShipRecord(mmsi, ship)
        {
            const style = shipMarkerStyle(ship);

            const entity = viewer.entities.add({
                id: "ship-" + mmsi,
                position: Cesium.Cartesian3.fromDegrees(ship.lon, ship.lat),
                label: style.label,
                point: style.point
            });

            const trailEntity = viewer.entities.add({
                id: "trail-" + mmsi,
                polyline: {
                    positions: [Cesium.Cartesian3.fromDegrees(ship.lon, ship.lat)],
                    width: 1,
                    material: Cesium.Color.RED,
                    clampToGround: true
                }
            });

            return {
                entity: entity,
                trailEntity: trailEntity,
                headingEntity: null,
                trailPositions: [
                    Cesium.Cartesian3.fromDegrees(ship.lon, ship.lat)
                ],
                lastStyleKey: styleKey(ship),
                inPool: false
            };
        }

        function activatePooledRecord(record, mmsi, ship)
        {
            record.entity.id = "ship-" + mmsi;
            record.entity.show = true;
            record.trailEntity.id = "trail-" + mmsi;
            record.trailEntity.show = true;

            if (record.headingEntity)
            {
                record.headingEntity.id = "heading-" + mmsi;
                record.headingEntity.show = false;
            }

            record.trailPositions = [
                Cesium.Cartesian3.fromDegrees(ship.lon, ship.lat)
            ];
            record.lastStyleKey = null;
            record.inPool = false;
        }

        function addShip(ship)
        {
            const mmsi = String(ship.mmsi);
            let record = entityPool.acquire();

            if (record)
                activatePooledRecord(record, mmsi, ship);
            else
                record = createShipRecord(mmsi, ship);

            ships[mmsi] = record;
            shipPayloads[mmsi] = ship;
            updateShip(ship);
        }

        function updateShip(ship)
        {
            const mmsi = String(ship.mmsi);
            shipPayloads[mmsi] = ship;
            const record = ships[mmsi];

            if (!record)
            {
                addShip(ship);
                return ship;
            }

            const position = Cesium.Cartesian3.fromDegrees(ship.lon, ship.lat);
            const updateDetail = shouldUpdateShipDetail(ship);

            record.entity.position = position;
            record.entity.show = true;
            applyDistanceDisplay(record);

            if (updateDetail)
            {
                applyShipStyle(record, ship);
                updateHeadingVector(record, ship, Cesium);

                record.trailPositions.push(position);

                if (record.trailPositions.length > TRAIL_POINT_LIMIT)
                    record.trailPositions.shift();

                record.trailEntity.show = true;
                record.trailEntity.polyline.positions = new Cesium.ConstantProperty(
                    record.trailPositions.slice()
                );
            }
            else
            {
                record.trailEntity.show = false;

                if (record.headingEntity)
                    record.headingEntity.show = false;
            }

            return ship;
        }

        function destroyRecord(record)
        {
            viewer.entities.remove(record.entity);
            viewer.entities.remove(record.trailEntity);

            if (record.headingEntity)
                viewer.entities.remove(record.headingEntity);
        }

        function removeShip(mmsi)
        {
            const key = String(mmsi);
            const record = ships[key];

            if (!record)
                return;

            entityPool.release(record);
            delete ships[key];
            delete shipPayloads[key];
        }

        function drainPool()
        {
            while (entityPool.size() > 0)
            {
                const record = entityPool.acquire();

                if (record)
                    destroyRecord(record);
            }
        }

        function clearShips()
        {
            for (const mmsi in ships)
                removeShip(mmsi);

            drainPool();

            for (const key in shipPayloads)
                delete shipPayloads[key];
        }

        function updateShips(list)
        {
            const active = new Set();

            for (const ship of list)
            {
                active.add(Number(ship.mmsi));

                if (ships[String(ship.mmsi)])
                    updateShip(ship);
                else
                    addShip(ship);
            }

            for (const mmsi in ships)
            {
                if (!active.has(Number(mmsi)))
                    removeShip(mmsi);
            }
        }

        function getRecord(mmsi)
        {
            return ships[String(mmsi)] || null;
        }

        function getPayload(mmsi)
        {
            return shipPayloads[String(mmsi)] || null;
        }

        function popupContent(ship)
        {
            if (ship && ship.popup_html)
                return ship.popup_html;

            return "";
        }

        function count()
        {
            return Object.keys(ships).length;
        }

        function poolSize()
        {
            return entityPool.size();
        }

        viewer.camera.changed.addEventListener(function()
        {
            for (const mmsi in ships)
                applyDistanceDisplay(ships[mmsi]);
        });

        return {
            addShip: addShip,
            updateShip: updateShip,
            removeShip: removeShip,
            clearShips: clearShips,
            updateShips: updateShips,
            getRecord: getRecord,
            getPayload: getPayload,
            popupContent: popupContent,
            count: count,
            poolSize: poolSize,
            drainPool: drainPool,
            initialize: function() {},
            activate: function() {},
            suspend: function() {},
            resume: function() {},
            shutdown: function()
            {
                clearShips();
            }
        };
    }

    global.createShipLayer = createShipLayer;
})(window);
