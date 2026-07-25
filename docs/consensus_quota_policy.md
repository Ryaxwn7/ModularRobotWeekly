# Consensus Quota Policy

Consensus is a high-value, quota-limited source in this project.

Rules:

- Monthly usage budget: 30 uses.
- Report budget: at most 2 Consensus searches per report by default.
- Cadence: Monday and Thursday.
- Before running a weekly report, check recent Consensus usage when available.
- The Consensus website currently reports 30 uses per month on the Free tier, resetting on the first day of the month.
- Search calls clearly count against the budget. Fetch calls are only used after search results are selected for citation.
- Each Consensus search should be broad enough to return useful papers across one full subfield.
- Do not use Consensus for quick exploratory searches when arXiv, Crossref, Semantic Scholar, or web search is enough.
- Record manual and automated Consensus use in `consensus_usage.json`, using `consensus_usage.example.json` as a template.

Preferred query pack:

1. Modular/reconfigurable robotics:
   `modular self-reconfigurable robot modular reconfigurable robotics Science Robotics IEEE Robotics and Automation Letters year:2024-2026`
2. Swarm intelligence:
   `swarm robotics collective intelligence multi-robot distributed control Nature Communications Science Robotics year:2024-2026`
3. Engineering/system design:
   `multi robot system engineering co-design modular robot hardware architecture Autonomous Robots IJRR year:2024-2026`

Monthly budget planning:

- 8 reports in a month: 2 searches per report = 16 searches.
- 9 reports in a month: 2 searches per report = 18 searches.
- 10 reports in a month: 2 searches per report = 20 searches.
- With a 30-use monthly limit, the twice-weekly schedule leaves room for manual searches and occasional deeper reports.
- If any manual Consensus searches were used in the same month, reduce that month's weekly automation budget accordingly.

Local automation note:

The local Python script cannot directly call the Codex Consensus connector. Consensus must be invoked by a Codex automation or by an interactive Codex session. The local script still generates a weekly report from public sources, and the Codex automation can merge Consensus findings into the final weekly brief.

Local source quality gates:

- Reject papers whose publication date is later than the report date.
- Reject public-source papers whose title or abstract does not contain a robotics signal such as robot, robotic, robotics, multi-robot, swarm robot, modular robot, or reconfigurable robot.
- Treat generic words such as system, architecture, optimization, control, modular, and swarm as weak signals unless they appear with robotics context.
