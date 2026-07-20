/**
 * SAVE-108 — Cesium IGlobeEngine orchestrator.
 */
(function(global)
{
    "use strict";

    const CESIUM_CAPABILITIES = {
        supports_globe: true,
        supports_pitch: true,
        supports_heading: true,
        supports_geodesic: true,
        supports_terrain: false,
        engine_id: "cesium"
    };

    function createCesiumEngine()
    {
        if (!global.Cesium)
            throw new Error("CesiumJS is not loaded.");

        const Cesium = global.Cesium;
        const container = document.getElementById("map");
        const popupElement = document.getElementById("vessel-popup");

        if (!container)
            throw new Error("Map container is missing.");

        container.innerHTML = "";

        const maptilerApiKey = global.__PROJECTX_MAPTILER_API_KEY__;
        if (!maptilerApiKey)
            throw new Error("MapTiler API key is not configured.");

        const streetsProvider = new Cesium.UrlTemplateImageryProvider({
            url: "https://api.maptiler.com/maps/streets-v2/256/{z}/{x}/{y}.png?key="
                + maptilerApiKey,
            credit: "© MapTiler © OpenStreetMap contributors",
            maximumLevel: 20
        });

        const viewer = new Cesium.Viewer(container, {
            baseLayer: Cesium.ImageryLayer.fromProviderAsync(streetsProvider),
            baseLayerPicker: false,
            geocoder: false,
            homeButton: false,
            sceneModePicker: false,
            navigationHelpButton: false,
            animation: false,
            timeline: false,
            fullscreenButton: false,
            vrButton: false,
            infoBox: false,
            selectionIndicator: false,
            terrainProvider: new Cesium.EllipsoidTerrainProvider(),
            requestRenderMode: true,
            maximumRenderTimeChange: Infinity
        });

        viewer.scene.globe.enableLighting = false;
        viewer.scene.fog.enabled = false;
        viewer.scene.globe.tileCacheSize = 100;
        viewer.scene.globe.preloadAncestors = false;
        viewer.scene.globe.preloadSiblings = false;
        viewer.cesiumWidget.creditContainer.style.display = "none";

        let bridge = null;
        let pendingPickLocation = null;
        const bridgeRef = { current: null };
        const lifecycle = global.createRendererLifecycle();
        const scene = global.createSceneGraph(viewer, Cesium, {
            popupElement: popupElement,
            bridge: bridgeRef
        });
        const renderTransaction = global.createRenderTransaction(scene);
        const rendererDiagnostics = global.createRendererDiagnostics(viewer, Cesium, {
            entityCounts: function()
            {
                return scene.entityCounts();
            },
            transactionQueueDepth: function()
            {
                return renderTransaction.queueDepth();
            }
        });

        global.__rendererDiagnostics = rendererDiagnostics;

        let pickHandler = null;

        lifecycle.register(scene.createLifecycleParticipant());
        lifecycle.register({
            initialize: function() {},
            activate: function()
            {
                viewer.useDefaultRenderLoop = true;
                scene.requestRender();
            },
            suspend: function()
            {
                viewer.useDefaultRenderLoop = false;
            },
            resume: function()
            {
                viewer.useDefaultRenderLoop = true;
                scene.requestRender();
            },
            shutdown: function()
            {
                if (pickHandler)
                    pickHandler.destroy();

                global.__rendererDiagnostics = null;
                global.__rendererLifecycle = null;

                if (!viewer.isDestroyed())
                    viewer.destroy();
            }
        });

        global.__rendererLifecycle = lifecycle;

        let pickEnabled = false;
        let headingPickEnabled = false;
        let headingPickOrigin = null;
        let pickMarkerEntity = null;
        let pickOverlayVisible = false;

        function reportPickLocation(latitude, longitude)
        {
            const bridgeObject = bridgeRef.current || bridge;

            if (bridgeObject && bridgeObject.reportLocation)
            {
                bridgeObject.reportLocation(latitude, longitude);
                pendingPickLocation = null;
                return;
            }

            pendingPickLocation = { lat: latitude, lon: longitude };
        }

        function reportPickHeading(heading)
        {
            const bridgeObject = bridgeRef.current || bridge;

            if (bridgeObject && bridgeObject.reportHeading)
                bridgeObject.reportHeading(heading);
        }

        function initBridge()
        {
            if (typeof qt === "undefined")
                return;

            new QWebChannel(qt.webChannelTransport, function(channel)
            {
                bridge = channel.objects.bridge;
                bridgeRef.current = bridge;

                if (pendingPickLocation && bridge && bridge.reportLocation)
                {
                    bridge.reportLocation(
                        pendingPickLocation.lat,
                        pendingPickLocation.lon
                    );
                    pendingPickLocation = null;
                }
            });
        }

        initBridge();

        function showEmptyOverlay(message)
        {
            const overlay = document.getElementById("empty-state");

            if (!overlay)
                return;

            if (message)
            {
                overlay.textContent = message;
                overlay.hidden = false;
            }
            else
            {
                overlay.textContent = "";
                overlay.hidden = true;
                overlay.classList.remove("map-empty-state--top");
                pickOverlayVisible = false;
            }
        }

        function showPickOverlay(message)
        {
            const overlay = document.getElementById("empty-state");

            if (!overlay)
                return;

            overlay.textContent = message || "";
            overlay.hidden = false;
            overlay.classList.add("map-empty-state--top");
            pickOverlayVisible = true;
        }

        function dismissPickOverlay()
        {
            if (!pickOverlayVisible)
                return;

            pickOverlayVisible = false;
            showEmptyOverlay("");
        }

        function clearPickMarker()
        {
            if (pickMarkerEntity)
            {
                viewer.entities.remove(pickMarkerEntity);
                pickMarkerEntity = null;
            }
        }

        function setPickMarker(lat, lon)
        {
            clearPickMarker();

            pickMarkerEntity = viewer.entities.add({
                id: "pick-marker",
                position: Cesium.Cartesian3.fromDegrees(lon, lat),
                point: {
                    pixelSize: 14,
                    color: Cesium.Color.fromCssColorString("#1e88e5"),
                    outlineColor: Cesium.Color.WHITE,
                    outlineWidth: 2,
                    disableDepthTestDistance: Number.POSITIVE_INFINITY
                }
            });

            scene.requestRender();
        }

        function enablePickMode(enabled)
        {
            pickEnabled = !!enabled;

            if (!pickEnabled)
                clearPickMarker();
        }

        function resetMapToWorldView()
        {
            scene.navigationLayer.resetWorldView();
            scene.requestRender();
        }

        function clearObservationPoints(message)
        {
            scene.clearObservationPoints();
            scene.coverageLayer.setVisible(true);
            resetMapToWorldView();
            showEmptyOverlay(message || "");
            scene.requestRender();
        }

        function updateObservationPoints(points)
        {
            const preservePickOverlay = pickEnabled || headingPickEnabled;

            if (!preservePickOverlay)
                showEmptyOverlay("");

            renderTransaction.queueObservations(points, {
                preservePickOverlay: preservePickOverlay
            });

            if (preservePickOverlay)
                return;

            if (points.length === 0)
                resetMapToWorldView();
        }

        function beginLocationPick(message)
        {
            headingPickEnabled = false;
            headingPickOrigin = null;
            pickEnabled = true;
            clearPickMarker();
            scene.coverageLayer.setVisible(true);
            showPickOverlay(message || "");
            resetMapToWorldView();
        }

        function beginHeadingPick(message, lat, lon)
        {
            pickEnabled = false;
            headingPickEnabled = true;
            headingPickOrigin = { lat: Number(lat), lon: Number(lon) };
            clearPickMarker();
            scene.cameraFrustumLayer.setPreview({
                id: "__preview__",
                lat: headingPickOrigin.lat,
                lon: headingPickOrigin.lon,
                heading_deg: 0,
                fov_deg: 90,
                max_distance_km: 5,
                enabled: true
            });
            showPickOverlay(message || "");
            scene.navigationLayer.flyToPoint({
                lat: headingPickOrigin.lat,
                lon: headingPickOrigin.lon
            });
            scene.requestRender();
        }

        function endHeadingPick()
        {
            headingPickEnabled = false;
            headingPickOrigin = null;
            scene.cameraFrustumLayer.clearPreview();
            showEmptyOverlay("");
            scene.requestRender();
        }

        function refreshLocationPickView(message)
        {
            pickEnabled = true;
            scene.coverageLayer.setVisible(true);
            showPickOverlay(message || "");
            resetMapToWorldView();
        }

        function endLocationPick()
        {
            pickEnabled = false;
            pendingPickLocation = null;
            clearPickMarker();
            scene.coverageLayer.setVisible(true);
            showEmptyOverlay("");
        }

        function setPickOverlay(message)
        {
            showPickOverlay(message || "");
        }

        function setCameraPreview(camera)
        {
            scene.cameraFrustumLayer.setPreview(camera);
            scene.requestRender();
        }

        function clearCameras()
        {
            renderTransaction.queueClearCameras();
        }

        function updateCameras(list)
        {
            renderTransaction.queueCameras(list);
        }

        function focusShip(mmsi)
        {
            scene.focusShip(mmsi);
        }

        pickHandler = new Cesium.ScreenSpaceEventHandler(viewer.scene.canvas);

        pickHandler.setInputAction(function(click)
        {
            if (headingPickEnabled && headingPickOrigin)
            {
                dismissPickOverlay();

                const picked = viewer.camera.pickEllipsoid(
                    click.position,
                    viewer.scene.globe.ellipsoid
                );

                if (!picked)
                    return;

                const cartographic = Cesium.Cartographic.fromCartesian(picked);
                const latitude = Cesium.Math.toDegrees(cartographic.latitude);
                const longitude = Cesium.Math.toDegrees(cartographic.longitude);
                const heading = global.CesiumGeodesic.bearingBetween(
                    headingPickOrigin.lat,
                    headingPickOrigin.lon,
                    latitude,
                    longitude
                );

                setCameraPreview({
                    id: "__preview__",
                    lat: headingPickOrigin.lat,
                    lon: headingPickOrigin.lon,
                    heading_deg: heading,
                    fov_deg: 90,
                    max_distance_km: 5,
                    enabled: true
                });
                reportPickHeading(heading);
                scene.requestRender();
                return;
            }

            if (pickEnabled)
            {
                dismissPickOverlay();

                const picked = viewer.camera.pickEllipsoid(
                    click.position,
                    viewer.scene.globe.ellipsoid
                );

                if (!picked)
                    return;

                const cartographic = Cesium.Cartographic.fromCartesian(picked);
                const latitude = Cesium.Math.toDegrees(cartographic.latitude);
                const longitude = Cesium.Math.toDegrees(cartographic.longitude);

                setPickMarker(latitude, longitude);
                reportPickLocation(latitude, longitude);
                return;
            }

            const pickedObject = viewer.scene.pick(click.position);

            if (!Cesium.defined(pickedObject) || !pickedObject.id)
            {
                scene.popupLayer.hide();
                return;
            }

            const entityId = String(pickedObject.id.id || "");

            if (!entityId.startsWith("ship-"))
            {
                scene.popupLayer.hide();
                return;
            }

            focusShip(Number(entityId.slice("ship-".length)));
        }, Cesium.ScreenSpaceEventType.LEFT_CLICK);

        viewer.camera.moveStart.addEventListener(function()
        {
            if (pickEnabled || headingPickEnabled)
                dismissPickOverlay();
        });

        resetMapToWorldView();

        return {
            getCapabilities: function()
            {
                return Object.assign({}, CESIUM_CAPABILITIES);
            },
            getLifecycle: function()
            {
                return lifecycle;
            },
            updateShips: function(list) { renderTransaction.queueShips(list); },
            removeShip: function(mmsi)
            {
                scene.shipLayer.removeShip(mmsi);
                scene.bearingLayer.removeBearing(mmsi);
                scene.requestRender();
            },
            clearShips: function()
            {
                scene.shipLayer.clearShips();
                scene.bearingLayer.clear();
                scene.popupLayer.hide();
                scene.requestRender();
            },
            updateObservationPoints: updateObservationPoints,
            clearObservationPoints: clearObservationPoints,
            updateCameras: updateCameras,
            clearCameras: clearCameras,
            beginLocationPick: beginLocationPick,
            endLocationPick: endLocationPick,
            beginHeadingPick: beginHeadingPick,
            endHeadingPick: endHeadingPick,
            refreshLocationPickView: refreshLocationPickView,
            enablePickMode: enablePickMode,
            setPickMode: enablePickMode,
            setPickOverlay: setPickOverlay,
            setPickMarker: setPickMarker,
            clearPickMarker: clearPickMarker,
            setCameraPreview: setCameraPreview,
            resetMapToWorldView: resetMapToWorldView,
            focusShip: focusShip,
            clearObservationPoint: clearObservationPoints,
            setObservationPoint: function(lat, lon)
            {
                updateObservationPoints([
                    {
                        id: "__legacy__",
                        name: "",
                        lat: lat,
                        lon: lon,
                        active: true
                    }
                ]);
            }
        };
    }

    global.createCesiumEngine = createCesiumEngine;
})(window);
