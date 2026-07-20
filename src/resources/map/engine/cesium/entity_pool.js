/**
 * SAVE-108 — Lightweight entity pool for Cesium layers.
 *
 * Reuses hidden entities instead of destroying and recreating them.
 */
(function(global)
{
    "use strict";

    function createEntityPool()
    {
        const available = [];

        function acquire()
        {
            if (available.length === 0)
                return null;

            const record = available.pop();
            record.inPool = false;
            return record;
        }

        function release(record)
        {
            if (!record || record.inPool)
                return;

            if (record.entity)
                record.entity.show = false;

            if (record.trailEntity)
                record.trailEntity.show = false;

            if (record.headingEntity)
                record.headingEntity.show = false;

            record.inPool = true;
            available.push(record);
        }

        function clear()
        {
            available.length = 0;
        }

        function size()
        {
            return available.length;
        }

        return {
            acquire: acquire,
            release: release,
            clear: clear,
            size: size
        };
    }

    global.createEntityPool = createEntityPool;
})(window);
