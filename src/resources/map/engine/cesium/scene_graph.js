/**
 * SAVE-108 — Cesium scene graph composition root.
 */
(function(global)
{
    "use strict";

    function createSceneGraph(viewer, Cesium, options)
    {
        const shipLayer = global.createShipLayer(viewer, Cesium);
        const observationLayer = global.createObservationLayer(viewer, Cesium);
        const coverageLayer = global.createCoverageLayer(viewer, Cesium);
        const bearingLayer = global.createBearingLayer(viewer, Cesium);
        const cameraFrustumLayer = global.createCameraFrustumLayer(viewer, Cesium);
        const popupLayer = global.createPopupLayer(
            viewer,
            Cesium,
            options.popupElement,
            options.bridge
        );
        const navigationLayer = global.createCameraLayer(viewer, Cesium);

        popupLayer.bindPostRender(function(mmsi)
        {
            const record = shipLayer.getRecord(mmsi);
            return record ? record.entity : null;
        });

        function requestRender()
        {
            viewer.scene.requestRender();
        }

        function referenceObservationPoint(points)
        {
            return points.find(function(point) { return point.reference; }) || null;
        }

        function updateShips(list)
        {
            shipLayer.updateShips(list);

            const reference = referenceObservationPoint(
                observationLayer.lastSyncedPoints || []
            );
            bearingLayer.setReferencePoint(reference);
            bearingLayer.sync(list);

            const openMmsi = popupLayer.openMmsi();

            if (openMmsi !== null)
            {
                const mmsi = String(openMmsi);
                const record = shipLayer.getRecord(mmsi);
                const ship = shipLayer.getPayload(mmsi);
                const html = shipLayer.popupContent(ship);

                popupLayer.refreshForShip(
                    mmsi,
                    html,
                    record ? record.entity : null
                );
            }

            requestRender();
        }

        function focusShip(mmsi)
        {
            const record = shipLayer.getRecord(mmsi);

            if (!record)
                return;

            navigationLayer.flyToShip(
                record.entity.position.getValue(viewer.clock.currentTime)
            );

            const ship = shipLayer.getPayload(mmsi);
            const html = shipLayer.popupContent(ship);

            if (html)
                popupLayer.show(mmsi, html, record.entity);
            else
                popupLayer.hide();

            requestRender();
        }

        function updateObservationPoints(points, renderOptions)
        {
            const preservePickOverlay = !!(renderOptions && renderOptions.preservePickOverlay);

            observationLayer.lastSyncedPoints = points.slice();
            observationLayer.sync(points);
            coverageLayer.sync(points);

            const reference = referenceObservationPoint(points);
            bearingLayer.setReferencePoint(reference);

            if (!preservePickOverlay)
                navigationLayer.focusObservationPoints(points, coverageLayer);

            requestRender();
        }

        function updateCameras(list)
        {
            cameraFrustumLayer.sync(list);
            requestRender();
        }

        function clearObservationPoints()
        {
            observationLayer.lastSyncedPoints = [];
            observationLayer.clear();
            coverageLayer.clear();
            bearingLayer.clear();
        }

        function clearCameras()
        {
            cameraFrustumLayer.clear();
        }

        function entityCounts()
        {
            return {
                ships: shipLayer.count(),
                ship_pool: shipLayer.poolSize(),
                observations: observationLayer.count(),
                coverage: coverageLayer.count(),
                bearings: bearingLayer.count(),
                camera_frustums: cameraFrustumLayer.count()
            };
        }

        function cleanup()
        {
            popupLayer.hide();
            shipLayer.drainPool();
        }

        function createLifecycleParticipant()
        {
            const layers = [
                shipLayer,
                observationLayer,
                coverageLayer,
                bearingLayer,
                cameraFrustumLayer,
                popupLayer,
                navigationLayer
            ];

            function invokeLayer(methodName)
            {
                for (const layer of layers)
                {
                    const handler = layer[methodName];

                    if (typeof handler === "function")
                        handler();
                }
            }

            return {
                initialize: function()
                {
                    invokeLayer("initialize");
                },
                activate: function()
                {
                    invokeLayer("activate");
                    requestRender();
                },
                suspend: function()
                {
                    invokeLayer("suspend");
                },
                resume: function()
                {
                    invokeLayer("resume");
                    requestRender();
                },
                shutdown: function()
                {
                    invokeLayer("shutdown");
                    cleanup();
                }
            };
        }

        return {
            shipLayer: shipLayer,
            observationLayer: observationLayer,
            coverageLayer: coverageLayer,
            bearingLayer: bearingLayer,
            cameraFrustumLayer: cameraFrustumLayer,
            popupLayer: popupLayer,
            navigationLayer: navigationLayer,
            requestRender: requestRender,
            updateShips: updateShips,
            focusShip: focusShip,
            updateObservationPoints: updateObservationPoints,
            updateCameras: updateCameras,
            clearObservationPoints: clearObservationPoints,
            clearCameras: clearCameras,
            entityCounts: entityCounts,
            cleanup: cleanup,
            createLifecycleParticipant: createLifecycleParticipant
        };
    }

    global.createSceneGraph = createSceneGraph;
})(window);
