import duckdb
conn = duckdb.connect('football_probability.duckdb', read_only=True)
res = conn.execute("SELECT match_id, status FROM matches WHERE match_phase='Group'").fetchall()
not_sim = [m for m in res if m[1] not in ('Simulated', 'Completed')]
print(len(res), 'total group matches')
print(len(not_sim), 'not simulated')
if not_sim:
    print(not_sim[:5])
