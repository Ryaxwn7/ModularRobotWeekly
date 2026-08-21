# Twice-Weekly Robotics Research Report Prompt

Generate the twice-weekly research report for robotics, focusing on:

- modular and self-reconfigurable robots
- swarm intelligence and swarm robotics
- multi-robot system engineering, co-design, control, hardware architecture, and theory
- biomimetic structure design and bio-inspired robotic mechanisms
- bio-inspired swarm algorithms, ant colony methods, particle swarm methods, and nature-inspired collective control

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
4. `biomimetic robot structure design bio-inspired robotic mechanism soft robot Science Robotics Nature Communications year:2024-2026`
5. `bio-inspired swarm robotics algorithm ant colony particle swarm multi-robot coordination year:2024-2026`

Topic rotation:

- Monday: prefer searches 1 and 2.
- Thursday: prefer searches 3 and 4.
- If the previous report had few biomimetic or swarm-algorithm papers, use search 5 instead of one lower-yield query.
- If the local public-source report shows a clear spike in another topic, replace one query with the most relevant recommended query, but still stay within 2 searches.

After Consensus search:

1. Run the local project command:
   `python -m daily_research_agent --config config.weekly.json --days 4`
2. Merge the Consensus findings into `site/data/papers.json`, preserving existing high-quality items and updating or inserting new papers by stable id or DOI.
   - Treat Consensus only as a discovery source. Never use a `consensus.app` URL as the paper's original link.
   - Resolve and verify the version-of-record DOI from Crossref or the publisher when available, then store `url` and `doi_url` as `https://doi.org/<DOI>`.
   - For papers without a DOI, use the official arXiv abstract page or the publisher's article page. If no original source can be verified, leave `url` empty.
3. Combine the local report with the Consensus findings.
4. Update `consensus_usage.json` with the month, date, purpose, and number of Consensus search calls used.
5. Prioritize Science Robotics, Nature, IEEE RA-L, IEEE T-RO, IJRR, Autonomous Robots, Advanced Intelligent Systems, and Elsevier robotics venues.
6. Downgrade low-signal venues, generic reviews, and papers without clear robotics validation.
7. Write a concise Chinese weekly report with:
   - executive summary
   - top 8-12 papers
   - algorithm / structure / system / theory tags
   - why each paper matters
   - links and citation metadata
   - next-week tracking suggestions
8. Publish the updated local Codex results to GitHub by running:
   `powershell -ExecutionPolicy Bypass -File .\scripts\publish_site_data.ps1 -Message "Update site data from Codex weekly report"`

Important: GitHub Actions must only deploy the existing `site/` directory. Do not rely on GitHub Actions to run the paper search, because it cannot access the Codex Consensus connector.
