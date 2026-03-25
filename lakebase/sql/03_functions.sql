-- available_slots: find open appointment slots for a shop
SET search_path TO hair_salon;

CREATE OR REPLACE FUNCTION available_slots(
    p_shop_id UUID,
    p_from TIMESTAMPTZ,
    p_to TIMESTAMPTZ,
    p_service_ids UUID[],
    p_staff_id UUID DEFAULT NULL
)
RETURNS TABLE (
    staff_id UUID,
    staff_name TEXT,
    slot_start TIMESTAMPTZ,
    slot_end TIMESTAMPTZ
)
LANGUAGE plpgsql
AS $$
DECLARE
    v_total_minutes INTEGER;
    v_num_services INTEGER;
BEGIN
    v_num_services := array_length(p_service_ids, 1);

    SELECT COALESCE(SUM(s.duration_minutes), 0)
    INTO v_total_minutes
    FROM services s
    WHERE s.id = ANY(p_service_ids) AND s.is_active;

    IF v_total_minutes = 0 THEN
        RETURN;
    END IF;

    RETURN QUERY
    WITH eligible_staff AS (
        SELECT st.id AS staff_id, st.full_name AS staff_name
        FROM staff st
        WHERE st.shop_id = p_shop_id
          AND st.is_active
          AND (p_staff_id IS NULL OR st.id = p_staff_id)
          AND (
              SELECT COUNT(DISTINCT ss.service_id)
              FROM staff_services ss
              WHERE ss.staff_id = st.id
                AND ss.service_id = ANY(p_service_ids)
          ) = v_num_services
    ),
    date_range AS (
        SELECT d::date AS day
        FROM generate_series(p_from::date, p_to::date, '1 day'::interval) d
    ),
    schedule_windows AS (
        SELECT
            es.staff_id,
            es.staff_name,
            (dr.day + sch.start_time) AT TIME ZONE 'Europe/Rome' AS window_start,
            (dr.day + sch.end_time) AT TIME ZONE 'Europe/Rome' AS window_end
        FROM eligible_staff es
        JOIN date_range dr ON true
        JOIN staff_schedules sch
            ON sch.staff_id = es.staff_id
            AND sch.day_of_week = EXTRACT(ISODOW FROM dr.day)::INT - 1
    ),
    candidate_slots AS (
        SELECT
            sw.staff_id,
            sw.staff_name,
            gs AS slot_start,
            gs + (v_total_minutes || ' minutes')::interval AS slot_end
        FROM schedule_windows sw
        CROSS JOIN LATERAL generate_series(
            sw.window_start,
            sw.window_end - (v_total_minutes || ' minutes')::interval,
            '30 minutes'::interval
        ) gs
        WHERE gs >= p_from
          AND gs + (v_total_minutes || ' minutes')::interval <= p_to
    )
    SELECT
        cs.staff_id,
        cs.staff_name,
        cs.slot_start,
        cs.slot_end
    FROM candidate_slots cs
    WHERE NOT EXISTS (
        SELECT 1
        FROM appointments a
        WHERE a.staff_id = cs.staff_id
          AND a.status NOT IN ('cancelled', 'no_show')
          AND tstzrange(a.start_time, a.end_time) && tstzrange(cs.slot_start, cs.slot_end)
    )
    ORDER BY cs.slot_start, cs.staff_name;
END;
$$;
