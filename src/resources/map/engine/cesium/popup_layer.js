/**
 * SAVE-108 — Screen-space popup layer for vessel cards.
 */
(function(global)
{
    "use strict";

    const POSITION_INTERVAL_FRAMES = 2;

    function createPopupLayer(viewer, Cesium, popupElement, bridge)
    {
        let openPopupMmsi = null;
        let cachedHtml = "";
        let frameCounter = 0;

        function attachLogbookHandlers(root)
        {
            const bridgeObject = bridge && bridge.current ? bridge.current : bridge;

            if (!root || !bridgeObject || !bridgeObject.openLogbook)
                return;

            root.querySelectorAll(".vessel-card__logbook-btn").forEach(function(btn)
            {
                btn.onclick = function()
                {
                    const mmsi = Number(btn.getAttribute("data-mmsi"));

                    if (Number.isFinite(mmsi))
                        bridgeObject.openLogbook(mmsi);
                };
            });
        }

        function hide()
        {
            openPopupMmsi = null;
            cachedHtml = "";

            if (!popupElement)
                return;

            popupElement.hidden = true;
            popupElement.innerHTML = "";
        }

        function position(entity)
        {
            if (!popupElement || !entity)
                return;

            const position = entity.position && entity.position.getValue(
                viewer.clock.currentTime
            );

            if (!position)
                return;

            const canvasPosition = Cesium.SceneTransforms.worldToWindowCoordinates(
                viewer.scene,
                position
            );

            if (!canvasPosition)
            {
                popupElement.hidden = true;
                return;
            }

            popupElement.style.left = canvasPosition.x + "px";
            popupElement.style.top = canvasPosition.y + "px";
            popupElement.hidden = false;
        }

        function show(mmsi, html, entity)
        {
            if (!popupElement || !html)
            {
                hide();
                return;
            }

            openPopupMmsi = Number(mmsi);

            if (html !== cachedHtml)
            {
                popupElement.innerHTML = html;
                cachedHtml = html;
                attachLogbookHandlers(popupElement);
            }

            popupElement.hidden = false;

            if (entity)
                position(entity);
        }

        function refreshForShip(mmsi, html, entity)
        {
            if (openPopupMmsi !== Number(mmsi))
                return;

            if (html)
                show(mmsi, html, entity);
            else
                hide();
        }

        function bindPostRender(getEntityForMmsi)
        {
            viewer.scene.postRender.addEventListener(function()
            {
                if (openPopupMmsi === null)
                    return;

                frameCounter += 1;

                if (frameCounter % POSITION_INTERVAL_FRAMES !== 0)
                    return;

                const entity = getEntityForMmsi(openPopupMmsi);

                if (entity)
                    position(entity);
            });
        }

        return {
            hide: hide,
            show: show,
            refreshForShip: refreshForShip,
            bindPostRender: bindPostRender,
            openMmsi: function() { return openPopupMmsi; },
            initialize: function() {},
            activate: function() {},
            suspend: function()
            {
                hide();
            },
            resume: function() {},
            shutdown: function()
            {
                hide();
            }
        };
    }

    global.createPopupLayer = createPopupLayer;
})(window);
