-- calculate the avg energy difference per hour of the day
select
  -- now() time_sec,
	CAST(time_hh as CHAR(50)) Tageszeit,
	avg(delta_l1_energy_2)    L1,
	avg(delta_l2_energy_2)    L2,
	avg(delta_l3_energy_2)    L3
from
	(
	-- lag the time and energy by one and calculate the difference
	select
		time_min,
		lag(time_hh, 1) over (order by time_min) time_hh,
		l1_energy_2_min,
		l2_energy_2_min,
		l3_energy_2_min,
		total_energy_2_min,
		lag(time_min , 1) over (order by time_min) time_lag,
		lag(l1_energy_2_min , 1) over (order by time_min) l1_energy_2_lag,
		lag(l2_energy_2_min , 1) over (order by time_min) l2_energy_2_lag,
		lag(l3_energy_2_min , 1) over (order by time_min) l3_energy_2_lag,
		lag(total_energy_2_min , 1) over (order by time_min) total_energy_2_lag,
		TIMEDIFF(time_min, lag(time_min, 1) over (order by time_min)) delta_time,
		l1_energy_2_min - lag(l1_energy_2_min, 1) over (order by time_min) delta_l1_energy_2,
		l2_energy_2_min - lag(l2_energy_2_min, 1) over (order by time_min) delta_l2_energy_2,
		l3_energy_2_min - lag(l3_energy_2_min, 1) over (order by time_min) delta_l3_energy_2,
		total_energy_2_min - lag(total_energy_2_min, 1) over (order by time_min) delta_total_energy_2
	from
		(
		-- calculate the minimum energy reading per (day, hour) group
		select
			min(CONVERT_TZ(time, 'UTC', 'Europe/Berlin')) time_min,
			min(l1_energy_2) l1_energy_2_min,
			min(l2_energy_2) l2_energy_2_min,
			min(l3_energy_2) l3_energy_2_min,
			min(total_energy_2) total_energy_2_min,
			-- calculate average time for all times in group, then take only the hour part
			hour(SEC_TO_TIME(AVG(TIME_TO_SEC(CONVERT_TZ(time, 'UTC', 'Europe/Berlin'))))) time_hh
		from
			measurements.data
		group by
			hour(CONVERT_TZ(time, 'UTC', 'Europe/Berlin')),
			day(CONVERT_TZ(time, 'UTC', 'Europe/Berlin'))
		order by
			min(CONVERT_TZ(time, 'UTC', 'Europe/Berlin'))
	) mintime
	) deltas
where
	delta_time < "01:00:05"
	and delta_time > "00:59:55"
group BY
	time_hh
