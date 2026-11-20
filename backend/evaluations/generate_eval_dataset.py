"""
Generates the 6 multi-category evaluation PDF documents for Phase 6 QA and evaluation.
Covers:
1. tech_sre_runbook.pdf (Technical documentation, CLI commands, error codes, SLAs)
2. business_quarterly_report.pdf (Financial reports, currency, multi-column, quarterly tables)
3. research_ai_paper.pdf (Academic paper, abstract, math formulas, sparse attention, benchmarks)
4. educational_operating_systems.pdf (CS lecture notes, paging, TLB, replacement algorithms)
5. scanned_compliance_certificate.pdf (Rasterized scanned document testing OCR capability)
6. cloud_sla_terms.pdf (Legal/Technical SLA contract, tier tables, credit structures)
"""

import os
import fitz  # PyMuPDF
from pathlib import Path

DATA_DIR = Path(__file__).parent / "data"
DATA_DIR.mkdir(parents=True, exist_ok=True)


def create_tech_sre_runbook():
    """5-page technical SRE runbook with error codes, CLI commands, thresholds, tables."""
    doc = fitz.open()

    # Page 1: Overview & Architecture
    p1 = doc.new_page(width=612, height=792)
    p1.insert_text((50, 60), "TitanCloud Incident Runbook — System Operations v4.2", fontsize=15)
    p1.insert_text((50, 90), "1. Architecture and Global Service Level Objectives", fontsize=12)
    p1.insert_text((50, 115), 
        "TitanCloud core microservices operate across 3 availability zones (us-east-1a, 1b, 1c).\n"
        "The overall service availability target is 99.95% uptime across rolling 30-day windows.\n"
        "Maximum allowable P99 API response latency is 150ms under normal operating load.\n"
        "If global error rate exceeds 0.5% for 3 consecutive minutes, a SEV-1 incident is triggered automatically.\n"
        "Primary incident commander rotation is managed via PagerDuty escalation policy 'SRE-Global-OnCall'.",
        fontsize=10
    )

    # Page 2: PostgreSQL High Availability & Failover
    p2 = doc.new_page(width=612, height=792)
    p2.insert_text((50, 60), "2. PostgreSQL Database Operations and Replication Lag", fontsize=12)
    p2.insert_text((50, 85),
        "Cluster: db-primary.prod.titancloud.internal (Port 5432)\n"
        "Replication Engine: Patroni 3.0 with etcd distributed consensus.\n"
        "Threshold: Replication lag exceeding 100MB triggers alert ERR_PG_REPLICA_LAG.\n\n"
        "Standard Remediation Procedure:\n"
        "1. Check cluster health:\n"
        "   patronictl -c /etc/patroni/db.yml list\n"
        "2. If primary node is degraded, execute manual switchover:\n"
        "   patronictl -c /etc/patroni/db.yml switchover --master db-node-01 --candidate db-node-02 --force\n"
        "3. Restart the replica if replication wal stream is stalled:\n"
        "   sudo systemctl restart patroni-replica.service\n"
        "4. Maximum tolerable switchover downtime is 15 seconds.",
        fontsize=10
    )

    # Page 3: Redis In-Memory Cache Eviction & Memory Leaks
    p3 = doc.new_page(width=612, height=792)
    p3.insert_text((50, 60), "3. Redis Cache Cluster Troubleshooting", fontsize=12)
    p3.insert_text((50, 85),
        "Cluster Name: redis-session-prod.titancloud.internal (Port 6379)\n"
        "Max Memory Allocation: 64GB per node across 6 shard nodes.\n"
        "Eviction Policy: volatile-lru with maxmemory-samples 10.\n"
        "Alert Code: ERR_REDIS_OOM_EVICTION triggers when used memory exceeds 92% capacity.\n\n"
        "CLI Diagnostics:\n"
        "  redis-cli -h 10.0.12.44 -p 6379 info memory\n"
        "  redis-cli -h 10.0.12.44 -p 6379 --bigkeys\n"
        "Emergency command to flush temporary session tokens without dropping cached credentials:\n"
        "  redis-cli -h 10.0.12.44 -p 6379 EVAL \"return redis.call('DEL', unpack(redis.call('KEYS', 'session:temp:*')))\" 0\n"
        "Note: FLUSHALL is strictly forbidden in production without VP approval.",
        fontsize=10
    )

    # Page 4: Kafka Event Stream Lag & Consumer Balancing
    p4 = doc.new_page(width=612, height=792)
    p4.insert_text((50, 60), "4. Kafka Message Bus & Consumer Group Rebalancing", fontsize=12)
    p4.insert_text((50, 85),
        "Topic: telemetry-events-v1 (Partitions: 48, Replication Factor: 3)\n"
        "Retention Period: 7 days (168 hours) or 500GB per partition.\n"
        "Alert Code: ERR_KAFKA_LAG_CRITICAL triggers when consumer lag exceeds 50,000 records.\n\n"
        "CLI Verification:\n"
        "  kafka-consumer-groups.sh --bootstrap-server kafka.prod:9092 --describe --group order-processor\n"
        "If rebalance storm occurs (heartbeat timeout > 30000ms), restart consumer deployment with:\n"
        "  kubectl rollout restart deployment/order-processor-worker -n telemetry\n"
        "Expected recovery stabilization time: 180 seconds.",
        fontsize=10
    )

    # Page 5: SRE Incident Severity Matrix (Structured Table)
    p5 = doc.new_page(width=612, height=792)
    p5.insert_text((50, 60), "5. SRE Incident Severity and Escalation Matrix", fontsize=12)
    p5.insert_text((50, 85),
        "| Severity | Description | Response SLA | Target Resolution | Escalation Contact |\n"
        "| SEV-1 | Complete customer outage (>10% traffic dropped) | 5 minutes | 1 hour | VP Engineering |\n"
        "| SEV-2 | Degraded core function or high latency (>300ms) | 15 minutes | 4 hours | Staff SRE On-Call |\n"
        "| SEV-3 | Minor feature disruption or single replica down | 1 hour | 24 hours | Squad Tech Lead |\n"
        "| SEV-4 | Cosmetic defect or non-critical batch delay | 24 hours | 7 business days | Backlog Grooming |\n\n"
        "Post-Incident Review: All SEV-1 and SEV-2 incidents require a blameless postmortem published within 48 hours.",
        fontsize=9
    )

    out_path = DATA_DIR / "tech_sre_runbook.pdf"
    doc.save(str(out_path))
    doc.close()
    print(f"Generated {out_path} (5 pages)")


def create_business_quarterly_report():
    """3-page financial report with multi-column text, currencies, margins, tables."""
    doc = fitz.open()

    # Page 1: Executive Summary & Financial Highlights
    p1 = doc.new_page(width=612, height=792)
    p1.insert_text((50, 50), "Apex Global Technologies — Q3 2026 Earnings Report", fontsize=15)
    p1.insert_text((50, 75), "Period Ended September 30, 2026 | Reported November 12, 2026", fontsize=9)
    p1.insert_text((50, 105), "Executive Overview", fontsize=12)
    p1.insert_text((50, 125),
        "Apex Global recorded record third-quarter consolidated revenue of $42.8M, representing a 14.2% year-over-year\n"
        "increase compared to Q3 2025 revenue of $37.5M. The expansion was predominantly propelled by Enterprise Cloud\n"
        "Infrastructure subscriptions, which grew by 28.5% YoY.\n\n"
        "Key Financial Metrics:\n"
        "- Consolidated Revenue: $42.8M (vs $37.5M in Q3 2025)\n"
        "- Gross Profit Margin: 71.4% (up 180 basis points from 69.6%)\n"
        "- Operating Income: $12.4M with Operating Margin of 28.97%\n"
        "- Net Income: $9.8M, resulting in Diluted Earnings Per Share (EPS) of $0.46\n"
        "- Cash and Cash Equivalents: $118.5M as of September 30, 2026",
        fontsize=10
    )

    # Page 2: Segment Breakdown Table
    p2 = doc.new_page(width=612, height=792)
    p2.insert_text((50, 50), "Revenue Breakdown by Business Segment (in Millions USD)", fontsize=13)
    p2.insert_text((50, 80),
        "| Business Segment | Q3 2025 Revenue | Q3 2026 Revenue | YoY Growth (%) | Operating Margin |\n"
        "| Enterprise Cloud | $18.2M | $23.4M | +28.5% | 34.2% |\n"
        "| Managed Security | $11.1M | $12.5M | +12.6% | 24.8% |\n"
        "| Professional Services | $8.2M | $6.9M | -15.8% | 14.5% |\n"
        "| Total Consolidated | $37.5M | $42.8M | +14.2% | 28.97% |\n\n"
        "Analysis of Segment Results:\n"
        "Enterprise Cloud continues to be the primary growth driver, contributing 54.7% of total revenue.\n"
        "Professional Services declined due to automated self-service onboarding reducing reliance on consulting.\n"
        "R&D expenditure reached $8.6M, representing 20.1% of gross revenue.",
        fontsize=10
    )

    # Page 3: Balance Sheet & Future Guidance
    p3 = doc.new_page(width=612, height=792)
    p3.insert_text((50, 50), "Q4 2026 Financial Guidance & Balance Sheet Summary", fontsize=13)
    p3.insert_text((50, 80),
        "Full Fiscal Year 2026 and Q4 Outlook:\n"
        "- Expected Q4 Revenue: $45.0M to $47.5M\n"
        "- Expected Full Year 2026 Revenue: $172.0M to $175.0M\n"
        "- Projected Full Year Operating Margin: 29.5%\n"
        "- Planned Capital Expenditures: $4.2M allocated to GPU inference clusters in Dublin data center.\n\n"
        "Long-term Debt Obligations:\n"
        "Total long-term senior convertible notes stand at $35.0M at 3.25% fixed interest, maturing October 2029.\n"
        "The board of directors declared a quarterly dividend of $0.08 per share payable December 15, 2026.",
        fontsize=10
    )

    out_path = DATA_DIR / "business_quarterly_report.pdf"
    doc.save(str(out_path))
    doc.close()
    print(f"Generated {out_path} (3 pages)")


def create_research_ai_paper():
    """3-page academic AI research paper with equations, algorithms, abstract, benchmarks."""
    doc = fitz.open()

    # Page 1: Title, Abstract, Architecture
    p1 = doc.new_page(width=612, height=792)
    p1.insert_text((50, 50), "Sparse Attention in Low-Latency Runbook Synthesis", fontsize=14)
    p1.insert_text((50, 70), "Dr. Elena Rostova, Marcus Thorne | Institute for Advanced Machine Intelligence", fontsize=9)
    p1.insert_text((50, 100), "Abstract", fontsize=12)
    p1.insert_text((50, 120),
        "Transformer-based retrieval-augmented generation suffers from quadratic attention complexity O(N^2)\n"
        "as sequence length N grows. In mission-critical Site Reliability Engineering (SRE) applications,\n"
        "sub-second synthesis over thousands of pages is necessary. We propose DynaSparse-Attn, a dynamic\n"
        "sparse attention mechanism combining block-diagonal local attention with routing top-k global anchors.\n"
        "DynaSparse-Attn reduces time complexity to O(N sqrt(N)) while retaining 99.4% factual recall on technical\n"
        "troubleshooting benchmarks.",
        fontsize=10
    )
    p1.insert_text((50, 220), "1. Mathematical Formulation", fontsize=12)
    p1.insert_text((50, 240),
        "Given query Q, key K, and value V matrices in R^(N x d), attention weights A are computed as:\n"
        "  Attention(Q, K, V) = softmax( (Q * K^T) / sqrt(d) + M ) * V\n"
        "where M is a sparse masking matrix defined by:\n"
        "  M_ij = 0 if |i - j| <= W or j in TopK(AnchorScores(Q_i))\n"
        "  M_ij = -infinity otherwise.\n"
        "In our standard configuration, local window W = 128 tokens and anchor count K = 16 tokens.",
        fontsize=10
    )

    # Page 2: Benchmark Results & Hardware Configuration
    p2 = doc.new_page(width=612, height=792)
    p2.insert_text((50, 50), "2. Empirical Evaluation and Benchmark Results", fontsize=13)
    p2.insert_text((50, 80),
        "Experiments were conducted on 8x NVIDIA H100 80GB SXM5 GPUs interconnected via 3.2 Tbps InfiniBand.\n"
        "Models were evaluated on the SRE-Bench-100 dataset containing 1,000 synthetic infrastructure incidents.\n\n"
        "| Architecture | Context Window | Factual Accuracy (%) | Latency (ms) | VRAM Footprint |\n"
        "| Standard Dense Attention | 8k tokens | 94.2% | 412ms | 38.4GB |\n"
        "| FlashAttention-v2 | 8k tokens | 94.2% | 185ms | 22.1GB |\n"
        "| BigBird Sparse | 32k tokens | 91.8% | 142ms | 16.5GB |\n"
        "| DynaSparse-Attn (Ours) | 32k tokens | 96.1% | 68ms | 9.8GB |\n\n"
        "As shown, DynaSparse-Attn achieves a 6.05x latency speedup over standard dense attention and delivers\n"
        "96.1% factual accuracy, outperforming all baseline architectures.",
        fontsize=10
    )

    # Page 3: Ablation Study & Conclusion
    p3 = doc.new_page(width=612, height=792)
    p3.insert_text((50, 50), "3. Ablation Study & Conclusion", fontsize=13)
    p3.insert_text((50, 80),
        "Ablation Analysis:\n"
        "Removing the Top-K routing anchors decreases factual recall by 7.3% to 88.8%, proving that global anchors\n"
        "are essential for cross-document entity tracking.\n"
        "Varying local window size W from 64 to 256 yields diminishing latency returns above W = 128.\n\n"
        "Conclusion:\n"
        "DynaSparse-Attn provides a computationally efficient foundation for real-time document-grounded AI\n"
        "in low-latency enterprise environments. Source code is licensed under Apache 2.0.",
        fontsize=10
    )

    out_path = DATA_DIR / "research_ai_paper.pdf"
    doc.save(str(out_path))
    doc.close()
    print(f"Generated {out_path} (3 pages)")


def create_educational_notes():
    """3-page CS operating systems educational notes on memory management."""
    doc = fitz.open()

    # Page 1: Virtual Memory & Page Tables
    p1 = doc.new_page(width=612, height=792)
    p1.insert_text((50, 50), "CS 350: Operating Systems — Lecture 14: Virtual Memory & Paging", fontsize=14)
    p1.insert_text((50, 75), "Instructor: Prof. Angela Zhang | Fall 2026 Semester", fontsize=10)
    p1.insert_text((50, 105), "1. Concepts of Paging and Address Translation", fontsize=12)
    p1.insert_text((50, 125),
        "In modern operating systems, physical memory is partitioned into fixed-size frames (typically 4096 bytes or 4KB).\n"
        "Virtual address space is divided into pages of identical size.\n"
        "Virtual addresses consist of two components:\n"
        "1. Virtual Page Number (VPN) — high-order bits.\n"
        "2. Page Offset (Offset) — low-order bits (12 bits for a 4KB page size).\n\n"
        "The Memory Management Unit (MMU) translates VPN to Physical Frame Number (PFN) using the Page Table.\n"
        "If a referenced page is marked invalid in the page table, a Page Fault exception (trap 14 in x86) is raised.",
        fontsize=10
    )

    # Page 2: TLB & Effective Memory Access Time
    p2 = doc.new_page(width=612, height=792)
    p2.insert_text((50, 50), "2. Translation Lookaside Buffer (TLB) Performance", fontsize=13)
    p2.insert_text((50, 80),
        "A TLB is a high-speed hardware associative cache that stores recent VPN-to-PFN mappings.\n"
        "Typical TLB access time: 1 nanosecond (1ns).\n"
        "Main memory access time: 100 nanoseconds (100ns).\n\n"
        "Effective Access Time (EAT) Formula:\n"
        "  EAT = (TLB_Hit_Rate * (TLB_Time + Memory_Time)) + ((1 - TLB_Hit_Rate) * (TLB_Time + 2 * Memory_Time))\n\n"
        "Example Numerical Calculation:\n"
        "Given TLB hit rate of 98% (0.98), TLB access time of 1ns, and memory access time of 100ns:\n"
        "  Hit access: 1ns + 100ns = 101ns\n"
        "  Miss access: 1ns + 100ns + 100ns = 201ns\n"
        "  EAT = 0.98 * 101ns + 0.02 * 201ns = 98.98ns + 4.02ns = 103.0ns.",
        fontsize=10
    )

    # Page 3: Page Replacement Algorithms & Course Grading
    p3 = doc.new_page(width=612, height=792)
    p3.insert_text((50, 50), "3. Page Replacement Algorithms and Exam Policies", fontsize=13)
    p3.insert_text((50, 80),
        "When physical memory is full and a page fault occurs, an existing victim frame must be evicted.\n"
        "Common Algorithms:\n"
        "- FIFO (First-In, First-Out): Suffers from Belady's Anomaly where increasing frames increases faults.\n"
        "- Optimal (OPT / MIN): Evicts page not used for longest future duration. Theoretical benchmark only.\n"
        "- LRU (Least Recently Used): Evicts page unreferenced for longest past duration.\n"
        "- Clock (Second-Chance): Approximates LRU using reference bits with circular buffer.\n\n"
        "Course Grading Distribution:\n"
        "- Programming Projects (4 total): 40% (10% each)\n"
        "- Midterm Exam: 25%\n"
        "- Final Exam: 30%\n"
        "- Homework & Participation: 5%\n"
        "Late Submission Penalty: 15% reduction per 24-hour day past the deadline up to maximum 3 days.",
        fontsize=10
    )

    out_path = DATA_DIR / "educational_operating_systems.pdf"
    doc.save(str(out_path))
    doc.close()
    print(f"Generated {out_path} (3 pages)")


def create_scanned_compliance_certificate():
    """1-page simulated scanned document rasterized to image and saved as PDF (tests OCR engine)."""
    # Create temporary doc with certificate text
    temp_doc = fitz.open()
    p = temp_doc.new_page(width=612, height=792)
    p.insert_text((50, 60), "CERTIFICATE OF CONFORMANCE — SECURITY & COMPLIANCE", fontsize=14)
    p.insert_text((50, 90), "Audited Entity: InfraMind Cloud Infrastructure Services Inc.", fontsize=11)
    p.insert_text((50, 115), "Certificate Number: SOC2-2026-X99-AUDIT", fontsize=10)
    p.insert_text((50, 140), "Certification Standard: SOC 2 Type II & ISO/IEC 27001:2022", fontsize=10)
    p.insert_text((50, 165), "Audit Firm: Horizon Cybersecurity Auditors LLP (London, UK)", fontsize=10)
    p.insert_text((50, 195),
        "Audit Scope & Findings:\n"
        "Horizon Cybersecurity conducted an independent verification of trust services criteria.\n"
        "Evaluation Period: October 1, 2025 through September 30, 2026.\n"
        "Results: Zero critical non-conformities identified across all 114 security controls.\n"
        "Encryption Standard: AES-256 for data at rest, TLS 1.3 for data in transit.\n"
        "Physical Data Center Audit: Complete multi-factor biometric authentication enforced.\n"
        "Certificate Issue Date: October 18, 2026\n"
        "Expiration Date: October 17, 2027\n"
        "Authorized Auditor Signature: Marcus Sterling, Lead Security Auditor CISSP #489102",
        fontsize=10
    )

    # Render page as a pixmap (pure raster image)
    pix = p.get_pixmap(dpi=150)
    temp_doc.close()

    # Create new PDF that embeds the raster image as a scanned page (no text layer)
    scanned_doc = fitz.open()
    img_page = scanned_doc.new_page(width=612, height=792)
    img_page.insert_image(fitz.Rect(0, 0, 612, 792), pixmap=pix)

    out_path = DATA_DIR / "scanned_compliance_certificate.pdf"
    scanned_doc.save(str(out_path))
    scanned_doc.close()
    print(f"Generated {out_path} (1 page scanned image testing OCR)")


def create_cloud_sla_terms():
    """4-page legal/technical cloud service level agreement contract."""
    doc = fitz.open()

    # Page 1: Definitions & Scope
    p1 = doc.new_page(width=612, height=792)
    p1.insert_text((50, 50), "TitanCloud Service Level Agreement (SLA) & Terms of Service", fontsize=14)
    p1.insert_text((50, 75), "Effective Date: January 1, 2026 | Contract Version 5.1", fontsize=10)
    p1.insert_text((50, 105), "1. Scope and Definitions", fontsize=12)
    p1.insert_text((50, 125),
        "This Service Level Agreement governs the provision of TitanCloud Managed Services.\n"
        "Definitions:\n"
        "- Monthly Uptime Percentage: (Total Minutes in Month - Downtime Minutes) / Total Minutes in Month * 100.\n"
        "- Downtime: Continuous period of greater than 1 minute where tenant API requests return HTTP 5xx errors.\n"
        "- Scheduled Maintenance: Maintenance window communicated at least 5 business days in advance.\n"
        "Scheduled maintenance is capped at maximum 4 hours per calendar month and is excluded from downtime.",
        fontsize=10
    )

    # Page 2: Service Tiers Table & Uptime Commitments
    p2 = doc.new_page(width=612, height=792)
    p2.insert_text((50, 50), "2. Service Tiers and Uptime Guarantees", fontsize=13)
    p2.insert_text((50, 80),
        "| Service Tier | Monthly Fee per Core | Guaranteed Uptime | Support Response SLA | Disaster Recovery RTO |\n"
        "| Standard Tier | $24.00 | 99.0% | 4 hours (Business hours) | 12 hours |\n"
        "| Professional Tier | $48.00 | 99.9% | 1 hour (24x7) | 4 hours |\n"
        "| Enterprise Tier | $96.00 | 99.99% | 15 minutes (24x7 Dedicated) | 30 minutes |\n\n"
        "Enterprise Tier includes a dedicated Technical Account Manager (TAM) and automated multi-region hot failover.",
        fontsize=10
    )

    # Page 3: Service Credit Penalty Schedule
    p3 = doc.new_page(width=612, height=792)
    p3.insert_text((50, 50), "3. Service Credits and Penalty Reimbursements", fontsize=13)
    p3.insert_text((50, 80),
        "In the event TitanCloud fails to meet the guaranteed Monthly Uptime Percentage, Customer is entitled\n"
        "to a Service Credit calculated as a percentage of the monthly recurring charge (MRC):\n\n"
        "For Enterprise Tier:\n"
        "- Uptime between 99.9% and 99.99%: 10% Service Credit\n"
        "- Uptime between 99.0% and 99.9%: 25% Service Credit\n"
        "- Uptime less than 99.0%: 50% Service Credit\n\n"
        "For Professional Tier:\n"
        "- Uptime between 98.0% and 99.9%: 15% Service Credit\n"
        "- Uptime less than 98.0%: 30% Service Credit\n\n"
        "Credit Claims Procedure:\n"
        "Claims must be submitted within 30 days of the end of the affected billing month.\n"
        "Maximum cumulative Service Credit in any billing month is 50% of the customer's total MRC.",
        fontsize=10
    )

    # Page 4: Exclusions & Force Majeure
    p4 = doc.new_page(width=612, height=792)
    p4.insert_text((50, 50), "4. SLA Exclusions and Limitations of Liability", fontsize=13)
    p4.insert_text((50, 80),
        "SLA guarantees do not apply to downtime caused by:\n"
        "a) Customer misconfiguration, unapproved application code changes, or invalid database queries.\n"
        "b) Exceeding documented API rate quotas (default: 10,000 requests per minute per IP).\n"
        "c) Upstream DNS root server outages or general internet transit degradation beyond TitanCloud AS19823.\n"
        "d) Force Majeure events including natural disasters, acts of war, or government cyber mandates.\n\n"
        "Aggregate liability under this agreement is strictly limited to total fees paid by Customer during the\n"
        "six (6) months immediately preceding the event giving rise to liability.",
        fontsize=10
    )

    out_path = DATA_DIR / "cloud_sla_terms.pdf"
    doc.save(str(out_path))
    doc.close()
    print(f"Generated {out_path} (4 pages)")


if __name__ == "__main__":
    create_tech_sre_runbook()
    create_business_quarterly_report()
    create_research_ai_paper()
    create_educational_notes()
    create_scanned_compliance_certificate()
    create_cloud_sla_terms()
    print("All 6 evaluation PDF documents generated successfully in data directory.")
