/**
 * SAVE-108 — Camera frustum and orientation layer.
 */
(function(global)
{
    "use strict";

    const PREVIEW_ID = "__camera_preview__";

    function createCameraFrustumLayer(viewer, Cesium)
    {
        const cameras = {};
        let preview = null;
        let visible = true;

        function setVisible(enabled)
        {
            visible = !!enabled;

            for (const cameraId in cameras)
            {
                cameras[cameraId].marker.show = visible;
                cameras[cameraId].frustum.show = visible;
            }

            if (preview)
            {
                preview.marker.show = visible;
                preview.frustum.show = visible;
            }

            viewer.scene.requestRender();
        }

        function cameraDistanceKm(camera)
        {
            const distance = Number(camera.max_distance_km);

            if (Number.isFinite(distance) && distance > 0)
                return distance;

            return 5.0;
        }

        function cameraFovDeg(camera)
        {
            const fov = Number(camera.fov_deg);

            if (Number.isFinite(fov) && fov > 0)
                return fov;

            return 90.0;
        }

        function frustumPositions(camera)
        {
            const lat = Number(camera.lat);
            const lon = Number(camera.lon);
            const heading = Number(camera.heading_deg) || 0.0;
            const fov = cameraFovDeg(camera);
            const distanceKm = cameraDistanceKm(camera);
            const half = fov / 2.0;
            const left = global.CesiumGeodesic.destinationPoint(
                lat,
                lon,
                heading - half,
                distanceKm
            );
            const center = global.CesiumGeodesic.destinationPoint(
                lat,
                lon,
                heading,
                distanceKm
            );
            const right = global.CesiumGeodesic.destinationPoint(
                lat,
                lon,
                heading + half,
                distanceKm
            );

            return [
                lon, lat,
                left.lon, left.lat,
                center.lon, center.lat,
                right.lon, right.lat
            ];
        }

        function buildGraphics(camera, idPrefix)
        {
            const positions = frustumPositions(camera);
            const color = Cesium.Color.fromCssColorString("#ffb74d");

            const marker = viewer.entities.add({
                id: idPrefix + "-marker",
                position: Cesium.Cartesian3.fromDegrees(camera.lon, camera.lat),
                show: visible,
                label: {
                    text: "📷",
                    font: "18px sans-serif",
                    fillColor: color,
                    style: Cesium.LabelStyle.FILL,
                    verticalOrigin: Cesium.VerticalOrigin.CENTER,
                    horizontalOrigin: Cesium.HorizontalOrigin.CENTER,
                    rotation: Cesium.Math.toRadians(Number(camera.heading_deg) || 0.0),
                    disableDepthTestDistance: Number.POSITIVE_INFINITY
                }
            });

            const frustum = viewer.entities.add({
                id: idPrefix + "-frustum",
                show: visible,
                polygon: {
                    hierarchy: Cesium.Cartesian3.fromDegreesArray(positions),
                    material: color.withAlpha(0.18),
                    outline: true,
                    outlineColor: color.withAlpha(0.85),
                    outlineWidth: 1.5,
                    perPositionHeight: false,
                    height: 0.0,
                    heightReference: Cesium.HeightReference.CLAMP_TO_GROUND
                }
            });

            return { marker: marker, frustum: frustum };
        }

        function removeCamera(cameraId)
        {
            const key = String(cameraId);
            const record = cameras[key];

            if (!record)
                return;

            viewer.entities.remove(record.marker);
            viewer.entities.remove(record.frustum);
            delete cameras[key];
        }

        function clear()
        {
            for (const cameraId in cameras)
                removeCamera(cameraId);

            clearPreview();
        }

        function clearPreview()
        {
            if (!preview)
                return;

            viewer.entities.remove(preview.marker);
            viewer.entities.remove(preview.frustum);
            preview = null;
        }

        function updateCamera(camera)
        {
            if (camera.enabled === false)
            {
                removeCamera(camera.id);
                return;
            }

            const key = String(camera.id);
            removeCamera(key);
            cameras[key] = buildGraphics(camera, "camera-" + key);
        }

        function sync(list)
        {
            const active = new Set();

            for (const camera of list)
            {
                const key = String(camera.id);
                active.add(key);
                updateCamera(camera);
            }

            for (const cameraId in cameras)
            {
                if (!active.has(cameraId))
                    removeCamera(cameraId);
            }
        }

        function setPreview(camera)
        {
            clearPreview();
            preview = buildGraphics(camera, "camera-preview");
        }

        return {
            setVisible: setVisible,
            addCamera: updateCamera,
            updateCamera: updateCamera,
            removeCamera: removeCamera,
            clear: clear,
            sync: sync,
            setPreview: setPreview,
            clearPreview: clearPreview,
            count: function()
            {
                return Object.keys(cameras).length;
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

    global.createCameraFrustumLayer = createCameraFrustumLayer;
})(window);
