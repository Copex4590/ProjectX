/**
 * SAVE-108 — Read-only renderer diagnostics (Phase E).
 *
 * Completely separate from SceneGraph and RenderTransaction. Collects runtime
 * metrics without influencing rendering behaviour.
 */
(function(global)
{
    "use strict";

    const FRAME_SAMPLE_LIMIT = 60;

    function createRendererDiagnostics(viewer, Cesium, providers)
    {
        const frameTimesMs = [];
        const bridgeLatenciesMs = [];
        let lastFrameTimestamp = performance.now();
        let lastBridgeTimestamp = 0;

        viewer.scene.postRender.addEventListener(function()
        {
            const now = performance.now();
            const delta = now - lastFrameTimestamp;

            if (delta > 0)
            {
                frameTimesMs.push(delta);

                if (frameTimesMs.length > FRAME_SAMPLE_LIMIT)
                    frameTimesMs.shift();
            }

            lastFrameTimestamp = now;
        });

        function recordBridgeCall(startMs)
        {
            const elapsed = performance.now() - startMs;

            bridgeLatenciesMs.push(elapsed);

            if (bridgeLatenciesMs.length > FRAME_SAMPLE_LIMIT)
                bridgeLatenciesMs.shift();

            lastBridgeTimestamp = elapsed;
        }

        function average(values)
        {
            if (!values.length)
                return 0.0;

            let total = 0.0;

            for (const value of values)
                total += value;

            return total / values.length;
        }

        function computeFps()
        {
            const avgFrame = average(frameTimesMs);

            if (avgFrame <= 0)
                return 0.0;

            return 1000.0 / avgFrame;
        }

        function cameraState()
        {
            const camera = viewer.camera;
            const position = camera.positionCartographic;

            return {
                longitude_deg: Cesium.Math.toDegrees(position.longitude),
                latitude_deg: Cesium.Math.toDegrees(position.latitude),
                height_m: position.height,
                heading_deg: Cesium.Math.toDegrees(camera.heading),
                pitch_deg: Cesium.Math.toDegrees(camera.pitch),
                roll_deg: Cesium.Math.toDegrees(camera.roll)
            };
        }

        function memoryEstimateBytes()
        {
            if (performance.memory && Number.isFinite(performance.memory.usedJSHeapSize))
                return Math.round(performance.memory.usedJSHeapSize);

            return null;
        }

        function snapshot()
        {
            const entityCounts = providers.entityCounts
                ? providers.entityCounts()
                : {};

            return {
                fps: Number(computeFps().toFixed(2)),
                frame_time_ms: Number(average(frameTimesMs).toFixed(3)),
                bridge_latency_ms: Number(
                    (bridgeLatenciesMs.length
                        ? average(bridgeLatenciesMs)
                        : lastBridgeTimestamp
                    ).toFixed(3)
                ),
                entity_counts: entityCounts,
                memory_estimate: memoryEstimateBytes(),
                camera_state: cameraState(),
                transaction_queue_depth: providers.transactionQueueDepth
                    ? providers.transactionQueueDepth()
                    : 0
            };
        }

        return {
            recordBridgeCall: recordBridgeCall,
            snapshot: snapshot
        };
    }

    global.createRendererDiagnostics = createRendererDiagnostics;
})(window);
