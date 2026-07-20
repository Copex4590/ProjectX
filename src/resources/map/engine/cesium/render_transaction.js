/**
 * SAVE-108 — Internal render transaction batching for Cesium SceneGraph.
 *
 * Coalesces multiple layer updates from a single Python event loop tick into
 * one scene commit and render request. Not part of the public bridge contract.
 */
(function(global)
{
    "use strict";

    function createRenderTransaction(scene)
    {
        let frame = null;
        let scheduled = false;

        function emptyFrame()
        {
            return {
                ships: undefined,
                observations: undefined,
                observationOptions: undefined,
                cameras: undefined,
                clearCameras: false
            };
        }

        function beginFrame()
        {
            if (!frame)
                frame = emptyFrame();

            return frame;
        }

        function scheduleCommit()
        {
            if (scheduled)
                return;

            scheduled = true;

            queueMicrotask(function()
            {
                scheduled = false;
                commit();
            });
        }

        function commit()
        {
            if (!frame)
                return;

            const pending = frame;
            frame = null;

            if (pending.observations)
            {
                scene.updateObservationPoints(
                    pending.observations,
                    pending.observationOptions || {}
                );
            }

            if (pending.ships)
                scene.updateShips(pending.ships);

            if (pending.clearCameras)
                scene.clearCameras();

            if (pending.cameras)
                scene.updateCameras(pending.cameras);

            scene.requestRender();
        }

        function endFrame()
        {
            commit();
        }

        function queueShips(list)
        {
            beginFrame().ships = list;
            scheduleCommit();
        }

        function queueObservations(points, options)
        {
            const current = beginFrame();
            current.observations = points;
            current.observationOptions = options || {};
            scheduleCommit();
        }

        function queueClearCameras()
        {
            beginFrame().clearCameras = true;
            scheduleCommit();
        }

        function queueCameras(list)
        {
            beginFrame().cameras = list;
            scheduleCommit();
        }

        function queueDepth()
        {
            if (!frame)
                return scheduled ? 1 : 0;

            let depth = 0;

            if (frame.ships !== undefined)
                depth += 1;

            if (frame.observations !== undefined)
                depth += 1;

            if (frame.cameras !== undefined)
                depth += 1;

            if (frame.clearCameras)
                depth += 1;

            return depth;
        }

        return {
            beginFrame: beginFrame,
            endFrame: endFrame,
            commit: commit,
            queueShips: queueShips,
            queueObservations: queueObservations,
            queueCameras: queueCameras,
            queueClearCameras: queueClearCameras,
            queueDepth: queueDepth
        };
    }

    global.createRenderTransaction = createRenderTransaction;
})(window);
