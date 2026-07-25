# Twice-Weekly Robotics Research Report Prompt

Generate the twice-weekly research report for robotics, focusing on:

- modular and self-reconfigurable robots
- swarm intelligence and swarm robotics
- multi-robot system engineering, co-design, control, hardware architecture, and theory

Consensus quota policy:

- The user's Consensus quota is 30 uses per month on the Free tier.
- The quota resets on the first day of the month.
- Check `consensus_usage.json` if it exists, and account for manual searches already used this month.
- Use at most 2 Consensus search calls for this report.
- If fewer than 2 searches remain in the monthly budget, only use the remaining number.
- Do not run extra Consensus searches unless the user explicitly approves.
- Prefer broad, high-yield searches that return many relevant papers in one call.
- Use `year:2024-2026` unless a later current-year window is more appropriate.
- Fetch full records only for papers that will be cited in the report.

Recommended Consensus searches:

1. `modular self-reconfigurable robot modular reconfigurable robotics Science Robotics IEEE Robotics and Automation Letters year:2024-2026`
2. `swarm robotics collective intelligence multi-robot distributed control Nature Communications Science Robotics year:2024-2026`
3. `multi robot system engineering co-design modular robot hardware architecture Autonomous Robots IJRR year:2024-2026`

Topic rotation:

- Monday: prefer searches 1 and 2.
- Thursday: prefer searches 2 and 3.
- If the local public-source report shows a clear spike in another topic, replace one query with the most relevant recommended query, but still stay within 2 searches.

After Consensus search:

1. Run the local project command:
   `python -m daily_research_agent --config config.weekly.json --days 4`
2. Combine the local report with the Consensus findings.
3. Update `consensus_usage.json` with the month, date, purpose, and number of Consensus search calls used.
4. Prioritize Science Robotics, Nature, IEEE RA-L, IEEE T-RO, IJRR, Autonomous Robots, Advanced Intelligent Systems, and Elsevier robotics venues.
5. Downgrade low-signal venues, generic reviews, and papers without clear robotics validation.
6. Write a concise Chinese weekly report with:
   - executive summary
   - top 8-12 papers
   - algorithm / structure / system / theory tags
   - why each paper matters
   - links and citation metadata
   - next-week tracking suggestions
