"""
email_templates.py  (← job_hunter/emailer.py)

Templating only. The original SMTP send functions (`send_report_email`,
`send_error_alert`) are gone — delivery becomes a worker adapter over a
transactional provider (Resend) in Phase 4.4. What stays is the HTML body and
the subject line, as pure functions of the job list.
"""

from datetime import datetime


def build_report_subject(jobs: list[dict]) -> str:
    """The daily report subject line."""
    total = len(jobs)
    best_pct = max((j.get("match_percentage", 0) for j in jobs), default=0)
    best_company = (
        max(jobs, key=lambda x: x.get("match_percentage", 0)).get("company", "") if jobs else ""
    )
    urgent_count = sum(1 for j in jobs if j.get("urgency") == "HIGH")
    return (
        f"🎯 [{datetime.now().strftime('%b %d')}] {total} New Jobs | "
        f"Top: {best_company} ({best_pct}%) | "
        f"🔴 {urgent_count} Urgent"
    )


def build_report_email_html(jobs: list[dict], report_date: str) -> str:
    """Build an HTML email body with a summary + the top 5 matches."""
    total = len(jobs)
    high_match = [j for j in jobs if j.get("match_percentage", 0) >= 80]
    urgent_jobs = [j for j in jobs if j.get("urgency") == "HIGH"]
    best_job = max(jobs, key=lambda x: x.get("match_percentage", 0)) if jobs else {}

    top5 = sorted(jobs, key=lambda x: -x.get("match_percentage", 0))[:5]

    top5_rows = ""
    for j in top5:
        pct = j.get("match_percentage", 0)
        color = "#2e7d32" if pct >= 80 else "#f57c00" if pct >= 60 else "#757575"
        apply = j.get("apply_url", "#")
        top5_rows += f"""
        <tr>
          <td style="padding:8px;border-bottom:1px solid #eee;"><b>{j.get("company", "")}</b></td>
          <td style="padding:8px;border-bottom:1px solid #eee;">{j.get("title", "")}</td>
          <td style="padding:8px;border-bottom:1px solid #eee;color:{color};font-weight:bold;">{pct}%</td>
          <td style="padding:8px;border-bottom:1px solid #eee;">{j.get("location", "")}</td>
          <td style="padding:8px;border-bottom:1px solid #eee;">
            <a href="{apply}" style="background:#1565c0;color:white;padding:4px 10px;border-radius:4px;text-decoration:none;">Apply →</a>
          </td>
        </tr>"""

    best_callout = (
        ""
        if not best_job
        else f"""
    <div style="background:#e3f2fd;border-left:4px solid #1565c0;padding:14px;border-radius:0 8px 8px 0;margin-bottom:20px;">
      <b>🏆 Top Match Today:</b> {best_job.get("title", "")} at <b>{best_job.get("company", "")}</b>
      — <span style="color:#1565c0;font-weight:bold;">{best_job.get("match_percentage", 0)}% match</span>
      <br><a href="{best_job.get("apply_url", "#")}" style="color:#1565c0;">Apply Now →</a>
    </div>"""
    )

    return f"""
<!DOCTYPE html>
<html>
<head><meta charset="UTF-8"></head>
<body style="font-family:Arial,sans-serif;max-width:680px;margin:0 auto;background:#f5f5f5;">

  <div style="background:linear-gradient(135deg,#1565c0,#0d47a1);padding:28px;border-radius:12px 12px 0 0;text-align:center;">
    <h1 style="color:white;margin:0;font-size:24px;">🤖 Recruit-ME</h1>
    <p style="color:#bbdefb;margin:6px 0 0;">Daily Job Report — {report_date}</p>
  </div>

  <div style="background:white;padding:24px;border-radius:0 0 12px 12px;">

    <div style="display:flex;gap:12px;margin-bottom:24px;flex-wrap:wrap;">
      <div style="flex:1;background:#e8f5e9;padding:16px;border-radius:8px;text-align:center;min-width:130px;">
        <div style="font-size:28px;font-weight:bold;color:#2e7d32;">{total}</div>
        <div style="color:#555;font-size:13px;">Jobs Found</div>
      </div>
      <div style="flex:1;background:#fff8e1;padding:16px;border-radius:8px;text-align:center;min-width:130px;">
        <div style="font-size:28px;font-weight:bold;color:#f57f17;">{len(high_match)}</div>
        <div style="color:#555;font-size:13px;">80%+ Match 🟢</div>
      </div>
      <div style="flex:1;background:#fce4ec;padding:16px;border-radius:8px;text-align:center;min-width:130px;">
        <div style="font-size:28px;font-weight:bold;color:#c62828;">{len(urgent_jobs)}</div>
        <div style="color:#555;font-size:13px;">Apply Today 🔴</div>
      </div>
      <div style="flex:1;background:#e3f2fd;padding:16px;border-radius:8px;text-align:center;min-width:130px;">
        <div style="font-size:28px;font-weight:bold;color:#1565c0;">{best_job.get("match_percentage", 0)}%</div>
        <div style="color:#555;font-size:13px;">Best Match</div>
      </div>
    </div>

    {best_callout}

    <h3 style="color:#333;border-bottom:2px solid #1565c0;padding-bottom:8px;">⭐ Top Matches Today</h3>
    <table style="width:100%;border-collapse:collapse;font-size:13px;">
      <thead>
        <tr style="background:#1565c0;color:white;">
          <th style="padding:10px;text-align:left;">Company</th>
          <th style="padding:10px;text-align:left;">Role</th>
          <th style="padding:10px;text-align:left;">Match</th>
          <th style="padding:10px;text-align:left;">Location</th>
          <th style="padding:10px;text-align:left;"></th>
        </tr>
      </thead>
      <tbody>{top5_rows}</tbody>
    </table>

    <p style="color:#888;font-size:12px;margin-top:20px;">
      📎 Full list attached as an Excel file with {total} jobs, skills-gap analysis, and résumé tips.<br>
      🟢 Green = 80%+ | 🟡 Yellow = 60-79% | 🟠 Orange = 40-59%
    </p>

  </div>

  <p style="text-align:center;color:#aaa;font-size:11px;margin-top:12px;">
    Recruit-ME
  </p>
</body>
</html>"""
