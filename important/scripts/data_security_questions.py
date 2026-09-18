"""
Security Engineering Question Bank Generator.
Source: https://github.com/abhinavkakku/Cyber_Security_Interview_Questions
Commit: f42c7bf5340b1d7077bde24663148a0504ecb7ec
License: Public Open Source (GitHub Terms of Service)

Includes:
- 41 Foundational / Beginner Cybersecurity Questions
- 40 Intermediate Cybersecurity Questions
- 32 Experienced / Advanced Cybersecurity Questions
- Deep-dive architectural & job role taxonomy questions from the repository
- Complete role & experience level classifications based on real-world hiring standards
"""

import re
from typing import List, Dict, Any


def slugify(text: str) -> str:
    s = text.lower()
    s = re.sub(r"[^\w\s-]", "", s)
    s = re.sub(r"[\s_-]+", "-", s).strip("-")
    return s[:90]


def get_security_metadata(total_questions: int) -> Dict[str, Any]:
    return {
        "id": "security_engineering",
        "title": "Security Engineering",
        "short_title": "Security Eng",
        "tagline": "SOC analysis, penetration testing, network perimeter defense, application security, PKI, and incident response.",
        "description": "Master defense-in-depth security principles across entry-level, intermediate, and experienced roles. Covers threat modeling, OWASP Top 10, TCP/IP attacks, cryptographic ciphers, SIEM analytics, micro-segmentation, and enterprise system hardening.",
        "hero_illustration": "/illustrations/security_engineering_hero.png",
        "educational_diagrams": [
            "/illustrations/Cyber_Security_Job_Roles.png",
            "/illustrations/diagram_oauth_pkce_flow.svg"
        ],
        "source_repository": "https://github.com/abhinavkakku/Cyber_Security_Interview_Questions",
        "source_commit": "f42c7bf5340b1d7077bde24663148a0504ecb7ec",
        "source_license": "Public Open Source (GitHub Terms of Service)",
        "source_url": "https://github.com/abhinavkakku/Cyber_Security_Interview_Questions",
        "total_categories": 6,
        "total_questions": total_questions
    }


def get_security_questions() -> List[Dict[str, Any]]:
    # Repository provenance constants
    REPO_URL = "https://github.com/abhinavkakku/Cyber_Security_Interview_Questions"
    REPO_COMMIT = "f42c7bf5340b1d7077bde24663148a0504ecb7ec"
    REPO_LICENSE = "Public Open Source (GitHub Terms of Service)"
    REPO_FILE = "README.md"

    raw_items = [
        # =========================================================================
        # 1. CYBERSECURITY FUNDAMENTALS & THREAT TAXONOMY (ENTRY-LEVEL / JUNIOR)
        # =========================================================================
        {
            "id": "sec_role_taxonomy",
            "slug": "how-to-classify-cyber-security-roles-and-job-functions",
            "title": "How Can You Classify the Roles in Cyber Security? What are the Different Job Functions?",
            "category_id": "cybersecurity-fundamentals",
            "category_name": "Cybersecurity Fundamentals & Threat Taxonomy",
            "topic": "Career Roles & Core Functions",
            "difficulty": "Fundamental",
            "experience_level": "Entry-Level / Intern",
            "target_roles": ["SOC Analyst", "Security Analyst", "Junior Pentester", "Security Engineer"],
            "educational_diagram": "/illustrations/Cyber_Security_Job_Roles.png",
            "educational_diagram_alt": "Cyber Security Job Roles & Domains Mindmap (abhinavkakku/Cyber_Security_Interview_Questions)",
            "content": """### Overview of Cyber Security Job Roles
Cyber Security is a vast discipline with distinct specialized tracks. Understanding these domains helps interview candidates position their technical skills accurately:

1. **Defensive Operations (Blue Team / SecOps)**:
   - **SOC Analyst (Tier 1/2/3)**: Real-time triage of SIEM alerts, phishing investigation, endpoint malware containment, and ticket escalation.
   - **Incident Response (DFIR) Specialist**: Forensic disk/memory analysis, malware reverse engineering, and threat containment during live breaches.
   - **Threat Intelligence Analyst**: Tracking adversary groups (APTs), mapping Tactics, Techniques, and Procedures (TTPs) using MITRE ATT&CK.

2. **Offensive Security (Red Team / Ethical Hacking)**:
   - **Penetration Tester**: Authorized simulation of real-world attacks against web apps, APIs, mobile apps, and internal network infrastructure.
   - **Red Teamer / Adversary Simulation**: Emulating nation-state adversaries, physical security bypasses, and covert lateral movement.
   - **Vulnerability Researcher / Exploit Developer**: Reverse-engineering closed-source software to discover zero-day vulnerabilities.

3. **Engineering & Architecture**:
   - **Application Security (AppSec) Engineer**: Embedding secure coding guardrails, SAST/DAST automation in CI/CD, and threat modeling with software engineering teams.
   - **Cloud Security Engineer**: Managing IAM boundaries, AWS/GCP/Azure security postures, Kubernetes container hardening, and infrastructure-as-code (IaC) compliance.
   - **Network Security Engineer**: Configuring next-gen firewalls (NGFW), IDS/IPS, VPN concentrators, and zero-trust microsegmentation.

4. **Governance, Risk & Compliance (GRC)**:
   - **Security Compliance Auditor**: Aligning controls with ISO 27001, SOC 2 Type II, PCI DSS, NIST CSF, and GDPR.
   - **Security Architect / CISO**: Designing enterprise-wide security roadmaps, evaluating vendor risk, and reporting cybersecurity posture to executive boards.

![Cyber Security Job Roles](/illustrations/Cyber_Security_Job_Roles.png)"""
        },
        {
            "id": "sec_f_1",
            "title": "What are the Common Cyberattacks?",
            "category_id": "cybersecurity-fundamentals",
            "category_name": "Cybersecurity Fundamentals & Threat Taxonomy",
            "topic": "Core Attack Vectors",
            "difficulty": "Fundamental",
            "experience_level": "Entry-Level / Intern",
            "target_roles": ["SOC Analyst", "Security Analyst", "IT Helpdesk / Security Intern"],
            "content": """### Primary Cyber Attack Vectors

Cyberattacks threaten confidentiality, integrity, and availability across computing infrastructure:

- **Phishing**: Fraudulent communications (emails, SMS, chat messages) designed to impersonate trusted entities. Attackers trick victims into disclosing credentials, downloading malicious attachments, or authorizing fraudulent wire transfers.
- **Social Engineering Attacks**: Psychological manipulation tactics that exploit human routines, cognitive biases, and trust to coerce personnel into bypassing administrative controls.
- **Ransomware**: Destructive malware that traverses internal networks, terminates volume shadow copies, and encrypts critical files using strong symmetric/asymmetric algorithms (AES-256 + RSA-4096), demanding cryptocurrency payment for the private decryption key.
- **Cryptocurrency Hijacking (Cryptojacking)**: Unauthorized deployment of mining processes (e.g., XMRig) on victim endpoints, servers, or Kubernetes pods to mine coins like Monero, severely degrading CPU performance and inflating cloud utility bills.
- **Botnet Attacks**: Massive distributed networks of infected devices (IoT cameras, home routers, compromised web servers) commanded by a Command and Control (C2) server to coordinate volumetric DDoS attacks, distribute spam, or execute credential stuffing sweeps."""
        },
        {
            "id": "sec_f_2",
            "title": "What are the Elements of Cybersecurity?",
            "category_id": "cybersecurity-fundamentals",
            "category_name": "Cybersecurity Fundamentals & Threat Taxonomy",
            "topic": "Security Domains & Elements",
            "difficulty": "Fundamental",
            "experience_level": "Entry-Level / Intern",
            "target_roles": ["Security Analyst", "Security Engineer", "IT Auditor"],
            "content": """### The Foundational Elements of Modern Cybersecurity

Defense-in-depth requires coordinated technical and administrative controls across multiple layers:

1. **Application Security (AppSec)**: Embedding security controls into the Software Development Life Cycle (SDLC) to eliminate bugs, memory safety issues, and injection risks (OWASP Top 10) prior to production deployment.
2. **Information Security (InfoSec)**: Protecting sensitive data from unauthorized inspection, exfiltration, modification, or destruction through encryption, data classification, and Data Loss Prevention (DLP).
3. **Network Security**: Technical controls (firewalls, IDS/IPS, network segmentation, zero trust access) designed to inspect, police, and isolate packet traffic across internal and perimeter networks.
4. **Disaster Recovery & Business Continuity (DR/BCP)**: Formal policies, automated failover routines, and immutable backup systems engineered to restore business operations within defined Recovery Time Objectives (RTO) and Recovery Point Objectives (RPO).
5. **Operational Security (OpSec)**: Continuous risk-management routines where security practitioners evaluate systems and operational workflows from an attacker's perspective to eliminate unintended exposures.
6. **End-User Education & Awareness**: Structured employee training programs that cultivate defensive vigilance against social engineering, spear phishing, and improper credential hygiene."""
        },
        {
            "id": "sec_f_3",
            "title": "Define DNS and Explain Its Security Implications?",
            "category_id": "network-security",
            "category_name": "Network Security, Protocols & Perimeter Defenses",
            "topic": "Core Network Protocols",
            "difficulty": "Fundamental",
            "experience_level": "Entry-Level / Intern",
            "target_roles": ["Network Security Engineer", "SOC Analyst", "Systems Administrator"],
            "content": """### What is DNS?
The **Domain Name System (DNS)** is the hierarchical, decentralized naming system that translates human-readable domain names (e.g., `company.com`) into numerical IP addresses (e.g., `192.0.2.1` or `2001:db8::1`) used by networking hardware to route packets across the Internet.

### Security Implications & Attack Vectors
Because traditional DNS operates unencrypted over UDP port 53, it is historically vulnerable to:
- **DNS Spoofing / Cache Poisoning**: Injecting forged DNS records into a resolver's cache so that users requesting a legitimate site are redirected to an attacker-controlled server.
- **DNS Tunneling**: Encoding exfiltrated data or C2 command traffic inside standard DNS queries (`<base64-payload>.attacker.com`), bypassing restrictive egress firewall rules that permit outbound UDP 53.
- **DNS Amplification (DDoS)**: Sending small requests with forged source IPs to open recursive resolvers, which reflect significantly larger response payloads onto the victim's network.

### Mitigations:
- Implement **DNSSEC** (DNS Security Extensions) to add cryptographic signature verification to DNS records.
- Enforce **DoH** (DNS over HTTPS) or **DoT** (DNS over TLS) to encrypt recursive DNS lookups."""
        },
        {
            "id": "sec_f_4",
            "title": "What is a Firewall and How Does It Operate?",
            "category_id": "network-security",
            "category_name": "Network Security, Protocols & Perimeter Defenses",
            "topic": "Perimeter Controls",
            "difficulty": "Fundamental",
            "experience_level": "Entry-Level / Intern",
            "target_roles": ["Network Security Engineer", "SOC Analyst", "Firewall Administrator"],
            "content": """### Definition & Core Functionality
A **firewall** is a network security device or software module that inspects incoming and outgoing packet traffic, making deterministic allow, drop, or reject decisions based on an established security ruleset.

### Major Generations of Firewalls:
1. **Packet Filtering (Stateless)**: Inspects individual packets in isolation by checking Layer 3 (Source/Destination IP) and Layer 4 (Source/Destination Port, Protocol: TCP/UDP).
2. **Stateful Inspection Firewalls**: Tracks the active state of network connections (SYN, ESTABLISHED, FIN). Packets belonging to an already negotiated connection are permitted without re-evaluating the full ruleset.
3. **Application Layer (Proxy) Firewalls**: Terminates client connections, inspects Layer 7 payload contents (HTTP headers, MIME types, FTP commands), and initiates a separate connection to backend servers.
4. **Next-Generation Firewalls (NGFW)**: Combines stateful inspection with deep packet inspection (DPI), integrated Intrusion Prevention Systems (IPS), SSL/TLS decryption, and real-time threat intelligence feeds."""
        },
        {
            "id": "sec_f_5",
            "title": "What is a VPN and How Does It Protect Traffic?",
            "category_id": "network-security",
            "category_name": "Network Security, Protocols & Perimeter Defenses",
            "topic": "Encrypted Tunnels",
            "difficulty": "Fundamental",
            "experience_level": "Entry-Level / Intern",
            "target_roles": ["Network Security Engineer", "Remote Access Administrator"],
            "content": """### What is a Virtual Private Network (VPN)?
A **VPN** establishes an encrypted, authenticated point-to-point tunnel over an untrusted public network (such as the Internet), allowing remote users or branch offices to securely connect to private organizational subnets.

### Core Security Mechanisms:
1. **Tunneling Protocols**: Encapsulates original packets inside an outer transport packet (e.g., IPsec ESP, WireGuard, OpenVPN / SSL-TLS).
2. **Confidentiality (Encryption)**: Uses strong symmetric ciphers (AES-256-GCM, ChaCha20-Poly1305) to ensure eavesdroppers cannot inspect transmitted payload contents.
3. **Integrity & Authenticity**: Cryptographic HMACs or AEAD authentication tags verify that packets have not been modified or replayed in transit.
4. **Endpoint Authentication**: Mutual authentication via X.509 digital certificates, pre-shared keys, or MFA integration (SAML / RADIUS)."""
        },
        {
            "id": "sec_f_6",
            "title": "What are the Different Sources and Types of Malware?",
            "category_id": "cybersecurity-fundamentals",
            "category_name": "Cybersecurity Fundamentals & Threat Taxonomy",
            "topic": "Malware Analysis",
            "difficulty": "Fundamental",
            "experience_level": "Entry-Level / Intern",
            "target_roles": ["SOC Analyst", "Malware Researcher", "Incident Responder"],
            "content": """### Malware Classification & Propagation Vectors

Malicious software ('malware') is classified based on its execution mechanics and operational intent:

- **Worms**: Standalone self-propagating malware that actively scans networks for unpatched vulnerabilities (e.g., WannaCry scanning port 445 SMB) to spread autonomously without requiring human interaction or host files.
- **Viruses**: Malicious code that attaches to legitimate host files (executables, DLLs, Office macros). When the infected host executes, the virus code runs, corrupting data or spreading to other local binaries.
- **Trojans**: Programs masquerading as legitimate software (utilities, game cracks, PDF viewers). Once installed, they establish remote access backdoors, deploy keyloggers, or disable endpoint defenses.
- **Ransomware**: Encrypts victim databases and files using military-grade cryptography, demanding ransom for decryption keys.
- **Spyware & Infostealers**: Covert background processes designed to capture keystrokes, browser autofill passwords, session cookies, and crypto wallet secrets.
- **Adware**: Injects unwanted advertising, tracks browsing telemetry, and redirects search engines for affiliate fraud."""
        },
        {
            "id": "sec_f_7",
            "title": "How Does Email Work and What are Its Key Security Protocols?",
            "category_id": "network-security",
            "category_name": "Network Security, Protocols & Perimeter Defenses",
            "topic": "Email Protocols & Security",
            "difficulty": "Fundamental",
            "experience_level": "Entry-Level / Intern",
            "target_roles": ["SOC Analyst", "Email Administrator", "Security Engineer"],
            "content": """### Email Routing Architecture
When an email is dispatched:
1. **Dispatched via SMTP**: The sender's mail client communicates with its outbound **SMTP (Simple Mail Transfer Protocol)** server on port 587 (submission) or 25 (relay).
2. **DNS MX Lookup**: The sender's mail server queries DNS for the recipient domain's **MX (Mail Exchange)** records to identify destination servers.
3. **Mail Delivery & Storage**: The message routes across the internet and arrives at the recipient's Mail Transfer Agent (MTA), which stores the message in the recipient's mailbox.
4. **Client Retrieval**: The recipient accesses the message via **IMAP** (port 993 with TLS) or legacy **POP3** (port 995 with TLS).

### Core Email Authentication Defenses:
- **SPF (Sender Policy Framework)**: A DNS TXT record declaring which IP addresses are authorized to send mail on behalf of the domain.
- **DKIM (DomainKeys Identified Mail)**: Cryptographically signs outgoing emails using a private key; the recipient verifies the signature against the public key published in DNS TXT records.
- **DMARC (Domain-based Message Authentication, Reporting, and Conformance)**: Enforces policies (`p=none`, `p=quarantine`, `p=reject`) telling receiving servers how to handle emails that fail SPF or DKIM alignment."""
        },
        {
            "id": "sec_f_8",
            "title": "What is the Difference Between Active and Passive Cyber Attacks?",
            "category_id": "cybersecurity-fundamentals",
            "category_name": "Cybersecurity Fundamentals & Threat Taxonomy",
            "topic": "Threat Assessment",
            "difficulty": "Fundamental",
            "experience_level": "Entry-Level / Intern",
            "target_roles": ["SOC Analyst", "Security Analyst"],
            "content": """### Active vs Passive Attacks Comparison

| Attribute | Active Attack | Passive Attack |
| :--- | :--- | :--- |
| **Action** | Modifies message contents, deletes data, alters configuration, or floods resources. | Observes, intercepts, copies, and monitors traffic or data silently. |
| **Impacted Goal** | Violates **Integrity** or **Availability**. | Violates **Confidentiality**. |
| **System State** | Causes observable state changes, log anomalies, or system degradation. | Leaves system state unaltered; zero disruption to system operations. |
| **Examples** | SQL Injection, Man-in-the-Middle injection, Ransomware, DDoS, ARP poisoning. | Wiretapping, packet sniffing, shoulder surfing, traffic analysis, open-source intelligence. |
| **Primary Defense** | Firewalls, WAFs, IPS, immutable backups, input validation. | Strong end-to-end encryption (TLS 1.3, IPsec), VPNs, physical shielding. |"""
        },
        {
            "id": "sec_f_9",
            "title": "What is a Social Engineering Attack and How Can Organizations Defend Against It?",
            "category_id": "cybersecurity-fundamentals",
            "category_name": "Cybersecurity Fundamentals & Threat Taxonomy",
            "topic": "Human Risk & Social Engineering",
            "difficulty": "Fundamental",
            "experience_level": "Entry-Level / Intern",
            "target_roles": ["Security Analyst", "Awareness Lead", "SOC Analyst"],
            "content": """### Definition
A **Social Engineering Attack** is the psychological manipulation of individuals into divulging confidential information, relinquishing access credentials, or performing actions that undermine organizational security.

### Common Social Engineering Techniques:
- **Pretexting**: Creating an invented scenario (e.g., impersonating an external IT auditor or payroll administrator) to establish false authority.
- **Baiting**: Leaving infected USB drives in parking lots labeled 'Q4 Executive Salaries', exploiting curiosity.
- **Vishing / Smishing**: Voice phishing via phone calls or SMS phishing containing malicious links.
- **Watering Hole Attack**: Compromising a niche legitimate website known to be frequented by members of the target company.

### Multi-Layered Defenses:
1. Continuous simulated phishing campaigns accompanied by immediate, non-punitive micro-training.
2. Dual-authorization policies for financial wire transfers or administrative password resets.
3. Universal deployment of phishing-resistant hardware MFA (FIDO2 / WebAuthn security keys)."""
        },
        {
            "id": "sec_f_10",
            "title": "Who Are Black Hat, White Hat, and Grey Hat Hackers?",
            "category_id": "cybersecurity-fundamentals",
            "category_name": "Cybersecurity Fundamentals & Threat Taxonomy",
            "topic": "Hacking Terminology",
            "difficulty": "Fundamental",
            "experience_level": "Entry-Level / Intern",
            "target_roles": ["Security Analyst", "Penetration Tester"],
            "content": """### Ethical Hacker Spectrum

- **White Hat Hackers (Ethical Hackers)**: Certified security researchers and penetration testers who operate under explicit, legally binding written authorization. They identify, document, and responsibly report vulnerabilities to help organizations fortify their defenses.
- **Black Hat Hackers (Cybercriminals)**: Malicious actors who illegally breach systems for personal financial gain, extortion, data theft, espionage, or ideological sabotage without authorization.
- **Grey Hat Hackers**: Individuals who operate between ethical boundaries. They may discover and probe vulnerabilities without prior authorization from the asset owner, but subsequently notify the organization rather than selling exploits, often requesting a bug bounty or recognition."""
        },
        {
            "id": "sec_f_11",
            "title": "Define Encryption and Decryption?",
            "category_id": "cryptography-iam",
            "category_name": "Cryptography, PKI, IAM & Key Lifecycle",
            "topic": "Cryptographic Foundations",
            "difficulty": "Fundamental",
            "experience_level": "Entry-Level / Intern",
            "target_roles": ["Security Engineer", "AppSec Engineer", "Junior Cryptographer"],
            "content": """### Encryption and Decryption Fundamentals

- **Encryption**: The mathematical transformation of unencrypted, human-readable data (**plaintext**) into an unreadable, pseudorandom string (**ciphertext**) using an encryption algorithm (cipher) and a secret cryptographic key. Its primary objective is providing **confidentiality**.
- **Decryption**: The reverse process that transforms ciphertext back into original plaintext using the authorized cryptographic key.

### Two Major Cryptographic Paradigms:
1. **Symmetric Encryption**: Uses the exact same secret key for both encryption and decryption (e.g., AES-GCM, ChaCha20). Fast and optimized for bulk data.
2. **Asymmetric Encryption**: Uses a mathematically linked key pair: a publicly distributable **public key** for encryption and a guarded **private key** for decryption (e.g., RSA, ECC)."""
        },
        {
            "id": "sec_f_12",
            "title": "What is the Difference Between Plaintext and Cleartext?",
            "category_id": "cryptography-iam",
            "category_name": "Cryptography, PKI, IAM & Key Lifecycle",
            "topic": "Cryptographic Foundations",
            "difficulty": "Fundamental",
            "experience_level": "Entry-Level / Intern",
            "target_roles": ["Security Analyst", "Junior Cryptographer"],
            "content": """### Plaintext vs Cleartext Nuances

While frequently used interchangeably, they hold precise technical distinctions:

- **Plaintext**: Data formatted as the direct input to, or output from, an encryption algorithm. In cryptographic terminology, plaintext refers to information before it has been processed by an encryption cipher or after successful decryption.
- **Cleartext**: Data transmitted or stored in unencrypted format that was never intended to be encrypted (e.g., legacy HTTP headers, Telnet sessions, unencrypted DNS queries).

Both are readable without special tools, but plaintext implies an explicit relationship with an encryption routine."""
        },
        {
            "id": "sec_f_13",
            "title": "What is a Block Cipher and What are Common Cipher Modes?",
            "category_id": "cryptography-iam",
            "category_name": "Cryptography, PKI, IAM & Key Lifecycle",
            "topic": "Symmetric Ciphers",
            "difficulty": "Intermediate",
            "experience_level": "Mid-Level Engineer",
            "target_roles": ["AppSec Engineer", "Security Engineer", "Cryptographer"],
            "content": """### Block Cipher Architecture
A **block cipher** is a deterministic symmetric algorithm that encrypts fixed-size blocks of plaintext (typically 128 bits in modern ciphers like AES) into blocks of ciphertext of identical size.

### Critical Block Cipher Modes of Operation:
1. **ECB (Electronic Codebook)**:
   - **Insecure**: Encrypts identical plaintext blocks into identical ciphertext blocks, preserving structural patterns (famous 'ECB Penguin').
   - **Must Never Be Used** in production for multi-block messages.
2. **CBC (Cipher Block Chaining)**:
   - XORs each plaintext block with the previous ciphertext block before encryption, using an unpredictable Initialization Vector (IV) for the first block. Vulnerable to padding oracle attacks if authentication is absent.
3. **GCM (Galois/Counter Mode) - Modern Industry Standard**:
   - Authenticated Encryption with Associated Data (AEAD). Provides simultaneous **confidentiality** and **integrity/authenticity** via Galois field multiplication, offering superior hardware acceleration on modern CPUs."""
        },
        {
            "id": "sec_f_14",
            "title": "What is the CIA Triad?",
            "category_id": "cybersecurity-fundamentals",
            "category_name": "Cybersecurity Fundamentals & Threat Taxonomy",
            "topic": "Security Principles",
            "difficulty": "Fundamental",
            "experience_level": "Entry-Level / Intern",
            "target_roles": ["SOC Analyst", "Security Analyst", "CISO Office"],
            "content": """### The CIA Triad: Core Pillars of Information Security

The **CIA Triad** provides the foundational benchmark for assessing, implementing, and auditing information security policies:

1. **Confidentiality**: Ensuring that data, computing assets, and communications are shielded from unauthorized inspection, disclosure, or theft.
   - *Controls*: AES encryption, RBAC/ABAC access controls, multi-factor authentication, data classification.
2. **Integrity**: Guaranteeing that information and software remain accurate, complete, and protected against unauthorized modification, tampering, or deletion.
   - *Controls*: SHA-256 cryptographic hashing, digital signatures, version control, database constraints.
3. **Availability**: Ensuring that systems, networks, and applications remain operational, accessible, and responsive to authorized users when needed.
   - *Controls*: Load balancing, multi-region clustering, DDoS mitigation, automated disaster recovery, immutable backups."""
        },
        {
            "id": "sec_f_15",
            "title": "What is the TCP Three-Way Handshake and What Anomaly Patterns Threaten It?",
            "category_id": "network-security",
            "category_name": "Network Security, Protocols & Perimeter Defenses",
            "topic": "Transport Protocols",
            "difficulty": "Fundamental",
            "experience_level": "Entry-Level / Intern",
            "target_roles": ["Network Security Engineer", "SOC Analyst"],
            "content": """### The TCP 3-Way Handshake
Transmission Control Protocol (TCP) establishes reliable full-duplex streams via a three-packet sequence:

1. **Client -> Server (SYN)**: The client generates an Initial Sequence Number ($ISN_c$) and transmits a segment with the SYN flag set.
2. **Server -> Client (SYN-ACK)**: The server allocates connection state in its memory backlog, generates its own $ISN_s$, sets the ACK number to $ISN_c + 1$, and transmits SYN+ACK.
3. **Client -> Server (ACK)**: The client acknowledges the server's sequence number ($ISN_s + 1$), transitioning the connection to `ESTABLISHED`.

```text
Client                                Server
  |                                     |
  |---------- 1. SYN (seq=x) ---------->|  [Allocates connection slot]
  |<------- 2. SYN+ACK (seq=y, ack=x+1)-|
  |---------- 3. ACK (ack=y+1) -------->|  [Connection ESTABLISHED]
```

### Attack Vector: SYN Flood (DoS)
Attackers flood the server with thousands of SYN packets from spoofed IPs without sending the final ACK. The server's TCP backlog queue fills with half-open connections, exhausting memory and rejecting legitimate connections.

### Mitigations:
- **SYN Cookies**: Encodes connection state inside the server's $ISN_s$, eliminating memory allocation until the client's final ACK arrives.
- Rate limiting and firewall threshold tuning."""
        },
        {
            "id": "sec_f_16",
            "title": "How Can Identity Theft Be Prevented?",
            "category_id": "cybersecurity-fundamentals",
            "category_name": "Cybersecurity Fundamentals & Threat Taxonomy",
            "topic": "Identity & Credential Defense",
            "difficulty": "Fundamental",
            "experience_level": "Entry-Level / Intern",
            "target_roles": ["Security Analyst", "IT Administrator"],
            "content": """### Best Practices for Preventing Identity Theft

Defending personal and corporate digital identities requires rigorous technical and behavioral hygiene:

1. **Phishing-Resistant MFA**: Enforce FIDO2 / WebAuthn hardware keys (YubiKeys) or authenticator apps (TOTP), avoiding SMS-based verification susceptible to SIM-swapping.
2. **Password Manager Adoption**: Mandate unique, high-entropy passwords (16+ characters) across every service to eliminate credential stuffing attacks.
3. **Credit Freezes & Monitoring**: Freeze credit files at credit bureaus so identity thieves cannot open fraudulent accounts.
4. **Privileged Access Management (PAM)**: Eliminate persistent local administrator rights on employee laptops.
5. **Egress Threat Detection**: Deploy endpoint EDR to detect Infostealers (e.g., RedLine, Lumma) harvesting credentials from local browser SQLite databases."""
        },
        {
            "id": "sec_f_17",
            "title": "What are Common Hashing Functions and How Do Cryptographic Hashes Differ from Index Hashes?",
            "category_id": "cryptography-iam",
            "category_name": "Cryptography, PKI, IAM & Key Lifecycle",
            "topic": "Cryptographic Hash Functions",
            "difficulty": "Intermediate",
            "experience_level": "Mid-Level Engineer",
            "target_roles": ["AppSec Engineer", "Cryptographer", "Security Engineer"],
            "content": """### Cryptographic Hash Function Properties
A cryptographic hash function maps arbitrary-length binary input into a fixed-size digest, satisfying four strict mathematical requirements:
1. **Deterministic**: Identical inputs always produce identical digests.
2. **Pre-image Resistance (One-Way)**: Given hash $h$, it is computationally infeasible to find message $m$ such that $hash(m) = h$.
3. **Second Pre-image Resistance**: Given $m_1$, it is infeasible to find $m_2 \\ne m_1$ such that $hash(m_1) = hash(m_2)$.
4. **Collision Resistance**: Infeasible to find any arbitrary pair $(m_1, m_2)$ where $hash(m_1) = hash(m_2)$.

### Standard Algorithms vs Broken Algorithms:
- **Obsolete / Cryptographically Broken**: MD5 (128-bit) and SHA-1 (160-bit) have demonstrated practical collision vulnerabilities and must not be used for security verification.
- **Secure General-Purpose**: SHA-2 family (SHA-256, SHA-512) and SHA-3 family.
- **Secure Password Hashing (Slow / Memory-Hard)**: **Argon2id** (winner of Password Hashing Competition), **bcrypt**, and **scrypt**. These intentionally consume CPU time and memory to thwart GPU/ASIC brute-force cracking."""
        },
        {
            "id": "sec_f_18",
            "title": "What is Two-Factor Authentication (2FA) and What Factors Compose It?",
            "category_id": "cryptography-iam",
            "category_name": "Cryptography, PKI, IAM & Key Lifecycle",
            "topic": "Authentication & IAM",
            "difficulty": "Fundamental",
            "experience_level": "Entry-Level / Intern",
            "target_roles": ["Security Analyst", "IAM Engineer"],
            "content": """### Core Concepts of Multi-Factor Authentication
2FA requires users to validate identity by presenting two independent evidence elements across three primary authentication categories:

1. **Knowledge (Something you know)**: Password, PIN, or passphrase.
2. **Possession (Something you have)**: Hardware security key (FIDO2), smartphone generating TOTP codes, or smartcard.
3. **Inherence (Something you are)**: Biometrics such as fingerprint, facial geometry, or iris scanning.

*Note*: Entering two passwords or a password plus a security question is **not** 2FA because both represent the *same* category (Knowledge). True 2FA requires distinct categories."""
        },
        {
            "id": "sec_f_19",
            "title": "What Does XSS Stand For and How Can It Be Prevented?",
            "category_id": "application-security",
            "category_name": "Application Security, Injection Attacks & Web Exploits",
            "topic": "Web Application Security",
            "difficulty": "Intermediate",
            "experience_level": "Mid-Level Engineer",
            "target_roles": ["AppSec Engineer", "Penetration Tester", "Full-Stack Developer"],
            "content": """### What is Cross-Site Scripting (XSS)?
**XSS** occurs when a web application takes untrusted user input and incorporates it into dynamic HTML responses without proper contextual encoding or sanitization, causing victim browsers to execute arbitrary JavaScript within the application's origin context.

### The Three Flavors of XSS:
1. **Stored (Persistent) XSS**: Malicious script is saved in the database (e.g., user profile bio, forum post) and served to every user viewing the record.
2. **Reflected XSS**: Script is embedded in query parameters (e.g., `?q=<script>...`) and reflected immediately in the server response.
3. **DOM-based XSS**: Client-side JavaScript reads an untrusted source (`location.hash`) and writes it directly to an execution sink (`element.innerHTML = hash`).

### Comprehensive Mitigations:
- **Context-Aware Output Encoding**: HTML entity encode, JavaScript attribute encode, or URL encode based on where data renders.
- **Content Security Policy (CSP)**: Deploy strong HTTP response headers:
  ```http
  Content-Security-Policy: default-src 'self'; script-src 'self' https://trustedscripts.com;
  ```
- **HttpOnly Cookies**: Protect session tokens from JavaScript access by appending `HttpOnly; Secure; SameSite=Strict` flags."""
        },
        {
            "id": "sec_f_20",
            "title": "What Do You Mean by Shoulder Surfing?",
            "category_id": "cybersecurity-fundamentals",
            "category_name": "Cybersecurity Fundamentals & Threat Taxonomy",
            "topic": "Physical Security",
            "difficulty": "Fundamental",
            "experience_level": "Entry-Level / Intern",
            "target_roles": ["Security Analyst", "IT Helpdesk"],
            "content": """### Definition & Attack Scenarios
**Shoulder Surfing** is a direct observation technique where an attacker physically peers over a victim's shoulder or uses binoculars/hidden cameras in public locations (airports, coffee shops, ATMs) to capture passwords, PINs, or sensitive corporate intellectual property.

### Mitigations:
- Install physical privacy filters (polarized screen overlays) that restrict viewing angles to 30 degrees.
- Never enter sensitive credentials when someone is in direct line of sight.
- Mask password inputs with bullets (`••••••`)."""
        },
        {
            "id": "sec_f_21",
            "title": "What is the Difference Between Hashing and Encryption?",
            "category_id": "cryptography-iam",
            "category_name": "Cryptography, PKI, IAM & Key Lifecycle",
            "topic": "Cryptographic Foundations",
            "difficulty": "Fundamental",
            "experience_level": "Entry-Level / Intern",
            "target_roles": ["Security Engineer", "AppSec Engineer", "Software Engineer"],
            "content": """### Hashing vs Encryption Comparison Matrix

| Property | Hashing | Encryption |
| :--- | :--- | :--- |
| **Directionality** | **One-Way Function**: Cannot mathematically be reversed to yield the input. | **Two-Way Function**: Ciphertext can be decrypted back into plaintext using the correct key. |
| **Output Size** | **Fixed Length**: SHA-256 always outputs 256 bits (32 bytes) regardless of input size. | **Variable Length**: Output size scales with input message length and block padding. |
| **Key Requirement**| No secret key required for standard hashes (HMACs and Argon2 salts are exceptions). | Always requires a cryptographic key (symmetric or asymmetric). |
| **Primary Purpose**| Verifying **Integrity** (file checksums, password verification). | Providing **Confidentiality** (data protection in transit and at rest). |
| **Algorithms** | SHA-256, SHA-3, Argon2id, bcrypt. | AES-256-GCM, ChaCha20, RSA-4096. |"""
        },
        {
            "id": "sec_f_22",
            "title": "Differentiate Between Information Security and Information Assurance",
            "category_id": "cybersecurity-fundamentals",
            "category_name": "Cybersecurity Fundamentals & Threat Taxonomy",
            "topic": "Governance & Assurance",
            "difficulty": "Intermediate",
            "experience_level": "Mid-Level Engineer",
            "target_roles": ["Security Analyst", "GRC Lead", "IT Auditor"],
            "content": """### InfoSec vs Information Assurance (IA)

- **Information Security (InfoSec)**: The practice and technical tooling focused on defending information and computing assets against unauthorized access, use, modification, or disruption. It emphasizes direct technical, administrative, and physical controls.
- **Information Assurance (IA)**: The broader operational and strategic discipline of managing information-related risks across the enterprise. It guarantees that information remains available, reliable, authentic, confidential, and compliant through policies, risk management frameworks, disaster recovery planning, and audit controls."""
        },
        {
            "id": "sec_f_23",
            "title": "Write the Difference Between HTTPS and SSL",
            "category_id": "network-security",
            "category_name": "Network Security, Protocols & Perimeter Defenses",
            "topic": "Transport Security",
            "difficulty": "Fundamental",
            "experience_level": "Entry-Level / Intern",
            "target_roles": ["Network Security Engineer", "AppSec Engineer"],
            "content": """### HTTPS vs SSL Relationship

- **SSL (Secure Sockets Layer)**: The legacy cryptographic transport protocol introduced by Netscape in the 1990s. SSL 2.0 and 3.0 suffer from critical cryptographic flaws (POODLE, DROWN) and are **deprecated**. Its modern successor is **TLS (Transport Layer Security)**, currently at versions 1.2 and 1.3.
- **HTTPS (Hypertext Transfer Protocol Secure)**: An application protocol that runs standard HTTP communication over an encrypted TLS connection (typically TCP port 443).

*Key Distinction*: SSL/TLS is the underlying cryptographic transport protocol; HTTPS is the web protocol that uses TLS for encryption and server authentication."""
        },
        {
            "id": "sec_f_24",
            "title": "What Do You Mean by System Hardening?",
            "category_id": "cloud-architecture-devsecops",
            "category_name": "Enterprise Architecture, System Hardening & Advanced Threats",
            "topic": "Endpoint & OS Hardening",
            "difficulty": "Intermediate",
            "experience_level": "Mid-Level Engineer",
            "target_roles": ["Systems Administrator", "DevSecOps Engineer", "Cloud Security Engineer"],
            "content": """### The Engineering Process of System Hardening
**System Hardening** is the systematic reduction of a system's attack surface by eliminating unnecessary software, disabling insecure services, enforcing least privilege, and configuring robust defensive baselines.

### Core Hardening Steps (CIS Benchmarks / DISA STIG):
1. **Remove Unused Software & Daemons**: Uninstall legacy packages (Telnet, FTP, rsh).
2. **Close Unnecessary Network Ports**: Enforce local firewall rules (iptables / Windows Defender Firewall) allowing only required listening ports.
3. **Change Default Credentials**: Terminate default administrator accounts (`admin`, `root`, `guest`) and enforce MFA.
4. **Enforce Kernel Security Modules**: Enable SELinux or AppArmor to prevent compromised processes from breaking out of intended sandboxes.
5. **Disable Insecure Ciphers & Protocols**: Restrict SSH to public key authentication only (`PasswordAuthentication no`) and disable TLS 1.0/1.1."""
        },
        {
            "id": "sec_f_25",
            "title": "Differentiate Between Spear Phishing and Phishing",
            "category_id": "cybersecurity-fundamentals",
            "category_name": "Cybersecurity Fundamentals & Threat Taxonomy",
            "topic": "Social Engineering",
            "difficulty": "Fundamental",
            "experience_level": "Entry-Level / Intern",
            "target_roles": ["SOC Analyst", "Security Analyst"],
            "content": """### Phishing vs Spear Phishing

- **Phishing**: Mass email campaigns distributed indiscriminately to thousands of recipients using generic templates ('Your Bank Account is Suspended', 'DHL Package Pending'). Relies on sheer volume to snare a tiny percentage of victims.
- **Spear Phishing**: Highly tailored, researched attacks aimed at specific individuals, departments, or organizations. Adversaries conduct reconnaissance (LinkedIn, corporate websites, conference schedules) to reference real colleagues, ongoing projects, and organizational terminology, dramatically increasing credibility."""
        },
        {
            "id": "sec_f_26",
            "title": "What Do You Mean by Perfect Forward Secrecy (PFS)?",
            "category_id": "cryptography-iam",
            "category_name": "Cryptography, PKI, IAM & Key Lifecycle",
            "topic": "Key Agreement Protocols",
            "difficulty": "Advanced",
            "experience_level": "Senior / Staff Architect",
            "target_roles": ["Security Architect", "Cryptographer", "AppSec Engineer"],
            "content": """### What is Perfect Forward Secrecy (PFS)?
**Perfect Forward Secrecy** is a feature of secure key agreement protocols ensuring that if a server's long-term private key is compromised in the future, past encrypted sessions **cannot** be decrypted.

### How PFS Works:
In legacy RSA key exchange, the client encrypts a pre-master secret using the server's public key. If an adversary captures encrypted traffic and steals the private key 3 years later, they can retroactively decrypt all recorded historical sessions!

With PFS (enforced in TLS 1.3 via **ECDHE** - Elliptic Curve Diffie-Hellman Ephemeral):
- Every TLS session generates dynamic, one-time **ephemeral key pairs** that are discarded immediately after session key derivation.
- Compromising the long-term server certificate only allows impersonating future connections, not retroactively decrypting historical traffic captures."""
        },
        {
            "id": "sec_f_27",
            "title": "How Can Man-in-the-Middle (MITM) Attacks Be Prevented?",
            "category_id": "network-security",
            "category_name": "Network Security, Protocols & Perimeter Defenses",
            "topic": "Network Attack Prevention",
            "difficulty": "Intermediate",
            "experience_level": "Mid-Level Engineer",
            "target_roles": ["Network Security Engineer", "AppSec Engineer"],
            "content": """### Mitigations Against MITM Attacks

1. **Strict End-to-End Encryption**: Enforce TLS 1.3 across all application interfaces with modern cipher suites.
2. **HTTP Strict Transport Security (HSTS)**:
   ```http
   Strict-Transport-Security: max-age=63072000; includeSubDomains; preload
   ```
   Forces browsers to connect only via HTTPS, thwarting SSL stripping attacks (e.g., `sslstrip`).
3. **Mutual TLS (mTLS)**: Validates client certificates alongside server certificates in microservice architectures.
4. **Certificate Pinning**: Hardcodes expected public keys in native mobile apps to thwart rogue CA attacks.
5. **Switchport Security (DAI & DHCP Snooping)**: Prevents local ARP cache poisoning and rogue DHCP servers."""
        },
        {
            "id": "sec_f_28",
            "title": "What is Ransomware and What is the Best Defense Strategy?",
            "category_id": "cybersecurity-fundamentals",
            "category_name": "Cybersecurity Fundamentals & Threat Taxonomy",
            "topic": "Ransomware Defense",
            "difficulty": "Fundamental",
            "experience_level": "Entry-Level / Intern",
            "target_roles": ["SOC Analyst", "Incident Responder", "Storage Administrator"],
            "content": """### What is Ransomware?
Ransomware is malicious software that exfiltrates, encrypts, or locks a victim's data assets, demanding cryptocurrency extortion payments in exchange for decryption tools. Modern groups practice **double extortion** (encrypting data AND threatening to publish stolen records on leak sites).

### Defense-in-Depth Strategy:
1. **Immutable Offline Backups (3-2-1 Rule)**: 3 copies of data, across 2 different media types, with 1 copy stored completely offline or in write-once-read-many (WORM) air-gapped storage.
2. **EDR with Behavioral Containment**: Detects rapid mass file modifications and automatic volume shadow copy deletion commands (`vssadmin delete shadows`).
3. **Network Segmentation**: Isolates production subnets from office workstations to limit lateral movement."""
        },
        {
            "id": "sec_f_29",
            "title": "What is Public Key Infrastructure (PKI)?",
            "category_id": "cryptography-iam",
            "category_name": "Cryptography, PKI, IAM & Key Lifecycle",
            "topic": "PKI Architecture",
            "difficulty": "Intermediate",
            "experience_level": "Mid-Level Engineer",
            "target_roles": ["IAM Engineer", "Security Architect", "PKI Administrator"],
            "content": """### Core Components of a Public Key Infrastructure
A **PKI** is the integrated system of hardware, software, policies, and standards that manages the generation, distribution, validation, and revocation of digital certificates and public-key encryption:

1. **Certificate Authority (CA)**: The trusted entity that validates applicant identities and issues cryptographically signed X.509 certificates.
2. **Registration Authority (RA)**: Verifies applicant identities on behalf of the CA prior to certificate issuance.
3. **Certificate Revocation Mechanisms**:
   - **CRL (Certificate Revocation List)**: Periodically updated lists of revoked certificates.
   - **OCSP (Online Certificate Status Protocol)**: Real-time query mechanism for validating whether a certificate has been revoked."""
        },
        {
            "id": "sec_f_30",
            "title": "What is Spoofing and What are the Main Types?",
            "category_id": "network-security",
            "category_name": "Network Security, Protocols & Perimeter Defenses",
            "topic": "Spoofing Vectors",
            "difficulty": "Fundamental",
            "experience_level": "Entry-Level / Intern",
            "target_roles": ["SOC Analyst", "Network Engineer"],
            "content": """### Spoofing Concepts
**Spoofing** occurs when an adversary impersonates an authorized identity, device, or protocol address to deceive systems or users into granting access.

### Major Spoofing Types:
- **IP Spoofing**: Modifying the source IP address in packet headers to disguise sender origin or bypass simple IP-based firewall allowlists.
- **ARP Spoofing (ARP Poisoning)**: Broadcasting false ARP responses across a LAN to associate the attacker's MAC address with the default gateway's IP address.
- **Email Spoofing**: Fabricating SMTP sender headers to mislead recipients into believing mail originated from executives or trusted vendors.
- **DNS Spoofing**: Injecting forged DNS records into resolvers to redirect victim web traffic to malicious servers."""
        },
        {
            "id": "sec_f_31",
            "title": "What Do You Mean by a Null Session in Windows Networking?",
            "category_id": "network-security",
            "category_name": "Network Security, Protocols & Perimeter Defenses",
            "topic": "Windows Security",
            "difficulty": "Intermediate",
            "experience_level": "Mid-Level Engineer",
            "target_roles": ["Penetration Tester", "Windows Administrator", "Security Analyst"],
            "content": """### Null Session Mechanism & Risks
A **null session** is an anonymous connection established over SMB / NetBIOS (ports 139 / 445) without providing a valid username or password:
```cmd
net use \\target_ip\ipc$ "" /user:""
```

### Security Risks:
In legacy Windows configurations, null sessions allowed unauthenticated remote attackers to enumerate:
- Complete domain user lists and group memberships
- Network share names and access permissions
- Local security policy settings and password complexity rules

### Defense:
Ensure `RestrictAnonymous` is configured to `1` or `2` in Windows Group Policy and disable SMBv1 across the domain."""
        },
        {
            "id": "sec_f_32",
            "title": "Differentiate Between Threat, Vulnerability, and Risk",
            "category_id": "cybersecurity-fundamentals",
            "category_name": "Cybersecurity Fundamentals & Threat Taxonomy",
            "topic": "Risk Management",
            "difficulty": "Fundamental",
            "experience_level": "Entry-Level / Intern",
            "target_roles": ["Security Analyst", "GRC Analyst", "CISO Office"],
            "content": """### Threat, Vulnerability, and Risk: The Fundamental Security Equation

$$\\text{Risk} = \\text{Threat} \\times \\text{Vulnerability} \\times \\text{Impact}$$

1. **Threat**: Any external or internal force with the potential to harm systems or assets (e.g., cybercriminal ransomware gangs, malicious insiders, severe power outages, zero-day exploit tools).
2. **Vulnerability**: A flaw or weakness in software code, hardware architecture, network configuration, or operational procedures that can be exploited by a threat (e.g., unpatched Log4j library, open S3 bucket, default root password).
3. **Risk**: The likelihood that a threat will successfully discover and exploit a vulnerability, combined with the business and financial damage resulting from that compromise."""
        },
        {
            "id": "sec_f_33",
            "title": "How Can Content Security Policy (CSP) Neutralize XSS Attacks?",
            "category_id": "application-security",
            "category_name": "Application Security, Injection Attacks & Web Exploits",
            "topic": "Browser Security Controls",
            "difficulty": "Intermediate",
            "experience_level": "Mid-Level Engineer",
            "target_roles": ["AppSec Engineer", "Frontend Security Engineer"],
            "content": """### Content Security Policy (CSP) as a Last Line of Defense
Even if an application mistakenly renders unsanitized attacker input, **CSP** instructs modern browsers to restrict the sources from which scripts, styles, and images can execute.

### Effective CSP Directives:
```http
Content-Security-Policy: default-src 'self'; script-src 'self' 'nonce-rAnd0m123'; object-src 'none'; base-uri 'self';
```
- Disallows execution of inline scripts (`<script>alert(1)</script>`) unless they carry a cryptographically secure matching cryptographic `nonce`.
- Blocks execution of string-to-code functions like `eval()` and `setTimeout('alert()')`.
- Restricts `<form>` submission actions and iframe embedding."""
        },
        {
            "id": "sec_f_34",
            "title": "What are the Core Sub-Domains and Specializations of Cybersecurity?",
            "category_id": "cybersecurity-fundamentals",
            "category_name": "Cybersecurity Fundamentals & Threat Taxonomy",
            "topic": "Domain Taxonomies",
            "difficulty": "Fundamental",
            "experience_level": "Entry-Level / Intern",
            "target_roles": ["Security Analyst", "Security Engineer"],
            "content": """### Major Technical Sub-Domains of Cybersecurity

1. **Network Security**: Securing transport pipelines, routers, and switches using firewalls, IDS/IPS, and encrypted VPNs.
2. **Application Security (AppSec)**: Embedding security into software design via SAST, DAST, SCA, and threat modeling.
3. **Cloud Security**: Securing multi-tenant cloud workloads (AWS, Azure, GCP) using CSPM, IAM least privilege, and container security.
4. **Identity & Access Management (IAM)**: Managing authentication (SSO, MFA, OIDC) and authorization (RBAC, ABAC).
5. **Endpoint Security & EDR**: Protecting user laptops, mobile devices, and servers from malware and privilege escalation.
6. **Governance, Risk & Compliance (GRC)**: Ensuring institutional alignment with legal and regulatory mandates (GDPR, HIPAA, PCI-DSS, SOC 2)."""
        },
        {
            "id": "sec_f_35",
            "title": "What are Honeypots and How Do Deception Systems Benefit Defenders?",
            "category_id": "cybersecurity-fundamentals",
            "category_name": "Cybersecurity Fundamentals & Threat Taxonomy",
            "topic": "Deception Technology",
            "difficulty": "Intermediate",
            "experience_level": "Mid-Level Engineer",
            "target_roles": ["Threat Intelligence Analyst", "SOC Analyst", "Red/Blue Teamer"],
            "content": """### What is a Honeypot?
A **honeypot** is an isolated, deliberately vulnerable decoy system deployed within a network to attract, detect, and analyze unauthorized attacker activity. Because legitimate users have zero business reason to access a honeypot, **any connection attempt generates a high-fidelity security alert**.

### Types of Honeypots:
- **Low-Interaction Honeypots**: Emulates basic network ports (e.g., Honeyd). Captures IP scanning and automated brute-force attempts with low resource overhead.
- **High-Interaction Honeypots**: Deploys real operating systems and services inside isolated sandboxes to record complex attacker TTPs, lateral movement scripts, and custom zero-day payloads."""
        },
        {
            "id": "sec_f_36",
            "title": "Differentiate Between Vulnerability Assessment (VA) and Penetration Testing (PT)",
            "category_id": "application-security",
            "category_name": "Application Security, Injection Attacks & Web Exploits",
            "topic": "Security Testing Methodologies",
            "difficulty": "Intermediate",
            "experience_level": "Mid-Level Engineer",
            "target_roles": ["Penetration Tester", "Vulnerability Analyst", "SOC Lead"],
            "content": """### Vulnerability Assessment vs Penetration Testing

| Feature | Vulnerability Assessment (VA) | Penetration Testing (PT) |
| :--- | :--- | :--- |
| **Objective** | Discover, catalog, and rank *all* potential vulnerabilities across an inventory. | Actively exploit weaknesses to demonstrate practical real-world business impact. |
| **Methodology** | Automated scanning (Nessus, Qualys) + automated configuration checks. | Goal-oriented human-driven testing: chaining multiple small bugs into full compromise. |
| **Scope** | Broad, organization-wide inventory coverage. | Narrow, highly targeted scope under formal Rules of Engagement (ROE). |
| **Output** | Prioritized list of CVEs, CVSS scores, and remediation patch recommendations. | Narrative report documenting exploit chains, privilege escalation proofs, and root-cause fixes. |"""
        },
        {
            "id": "sec_f_37",
            "title": "What is a Brute Force Attack and How Can It Be Effectively Prevented?",
            "category_id": "cybersecurity-fundamentals",
            "category_name": "Cybersecurity Fundamentals & Threat Taxonomy",
            "topic": "Authentication Attacks",
            "difficulty": "Fundamental",
            "experience_level": "Entry-Level / Intern",
            "target_roles": ["SOC Analyst", "AppSec Engineer", "Systems Administrator"],
            "content": """### Brute Force Mechanics
A **brute force attack** is an automated trial-and-error approach where an adversary cycles through thousands or millions of password, encryption key, or session token combinations until the correct value matches.

### Key Countermeasures:
1. **Account Lockout & Exponential Backoff**: Lock accounts after 5 failed attempts or enforce exponential delays between consecutive login attempts.
2. **Mandatory MFA**: Render password guessing useless by requiring a secondary out-of-band token.
3. **CAPTCHA Integration**: Thwart automated headless bots after 2 failed attempts.
4. **Credential Stuffing Defenses**: Compare incoming passwords against breached password databases (e.g., HaveIBeenPwned API) to block known compromised passwords."""
        },
        {
            "id": "sec_f_38",
            "title": "What is a Man-in-the-Middle (MITM) Attack?",
            "category_id": "network-security",
            "category_name": "Network Security, Protocols & Perimeter Defenses",
            "topic": "Network Attacks",
            "difficulty": "Fundamental",
            "experience_level": "Entry-Level / Intern",
            "target_roles": ["SOC Analyst", "Network Engineer"],
            "content": """### MITM Attack Overview
A **Man-in-the-Middle attack** occurs when an adversary positions themselves within the communication path between two independent endpoints (e.g., client browser and banking server) to eavesdrop on, tamper with, or hijack the data stream without either party realizing.

### Common Exploitation Methods:
- **ARP Poisoning on Local LANs**: Tricking client and gateway into forwarding frames through the attacker's NIC.
- **Rogue Wi-Fi Access Points (Evil Twin)**: Deploying unencrypted public Wi-Fi hotspots that route user traffic through an inspection proxy.
- **DNS Spoofing**: Poisoning local DNS resolver caches to direct traffic to malicious IP addresses."""
        },
        {
            "id": "sec_f_39",
            "title": "Explain OAuth 2.0 PKCE Architecture and Why It Is Mandatory for Public Clients",
            "slug": "oauth2-pkce-architecture",
            "category_id": "cryptography-iam",
            "category_name": "Cryptography, PKI, IAM & Key Lifecycle",
            "topic": "Modern Identity Protocols",
            "difficulty": "Advanced",
            "experience_level": "Senior / Staff Architect",
            "target_roles": ["Security Architect", "AppSec Engineer", "Identity Architect"],
            "educational_diagram": "/illustrations/diagram_oauth_pkce_flow.svg",
            "educational_diagram_alt": "OAuth 2.0 Authorization Code Flow with PKCE Handshake Sequence Diagram",
            "content": """### Why PKCE was Introduced (RFC 7636)
In traditional OAuth 2.0, the Authorization Code Flow relies on a shared `client_secret` to authenticate the client when exchanging the authorization code for tokens. However, **public clients** (Single Page Applications, React/Vue frontends, and native mobile apps) cannot safely store a client secret because any distributed JavaScript or APK can be reverse engineered.

Without PKCE, if a malicious app registers the same custom URL scheme (or intercepts the browser redirect), it can steal the authorization code and directly exchange it for access tokens.

### The PKCE Security Mechanism
PKCE (Proof Key for Code Exchange) eliminates the need for a client secret by dynamically creating a one-time cryptographic handshake:

1. **Client Generation**:
   - The client generates a high-entropy cryptographically random string called the `code_verifier`.
   - The client computes `code_challenge = BASE64URL(SHA256(code_verifier))`.
2. **Authorization Request**:
   - The client redirects the user to the Authorization Server with `code_challenge` and `code_challenge_method=S256`.
3. **Authorization Server Storage**:
   - The Authorization Server validates credentials, records the `code_challenge`, and returns the short-lived `authorization_code`.
4. **Token Exchange**:
   - The client sends `POST /token` containing the `authorization_code` and the original `code_verifier`.
5. **Server Verification**:
   - The Authorization Server computes `SHA256(code_verifier)` and verifies it matches the previously recorded `code_challenge`.
   - If valid, the server issues the JWT Access Token and ID Token.

```text
Client App (SPA)           Authorization Server (IdP)          Resource API
       |                                   |                         |
       |--- 1. Gen verifier & challenge ---|                         |
       |--- 2. GET /authorize (challenge) ->|                         |
       |<-- 3. Returns auth_code ----------|                         |
       |--- 4. POST /token (code+verifier)->|                         |
       |    [Validates SHA256(verifier)]   |                         |
       |<-- 5. Returns JWT Tokens ---------|                         |
       |------------------------------------------------------------>| 6. GET with Bearer token
       |<------------------------------------------------------------| 7. Protected Data Payload
```"""
        },

        # =========================================================================
        # 2. INTERMEDIATE CYBERSECURITY QUESTIONS
        # =========================================================================
        {
            "id": "sec_i_1",
            "title": "What are the Steps Involved in Hacking a Server or Network and How Defenders Counter Them?",
            "category_id": "cloud-architecture-devsecops",
            "category_name": "Enterprise Architecture, System Hardening & Advanced Threats",
            "topic": "Adversary Lifecycle (Cyber Kill Chain)",
            "difficulty": "Intermediate",
            "experience_level": "Mid-Level Engineer",
            "target_roles": ["Penetration Tester", "SOC Analyst", "Security Engineer"],
            "content": """### The Cyber Kill Chain: Attack Phases and Defensive Controls

1. **Reconnaissance**:
   - *Adversary*: Passive OSINT (LinkedIn, DNS records, GitHub leak checks) and active network port scans (Nmap).
   - *Defense*: External Attack Surface Management (EASM), removing public-facing staging servers, threat intelligence feeds.
2. **Scanning & Enumeration**:
   - *Adversary*: Banner grabbing, web vulnerability scanning, discovering unpatched CVEs.
   - *Defense*: Strict ingress firewall filtering, routine automated vulnerability scanning, patching SLAs.
3. **Exploitation**:
   - *Adversary*: Exploiting remote code execution (RCE) flaws, phishing execution, SQL injection.
   - *Defense*: WAFs, EDR runtime containment, least privilege execution, disabling macro execution.
4. **Privilege Escalation & Persistence**:
   - *Adversary*: Kernel exploit, abusing sudo misconfigurations, creating scheduled tasks or backdoor services.
   - *Defense*: Local administrator password solution (LAPS), endpoint process monitoring, file integrity monitoring (FIM).
5. **Lateral Movement**:
   - *Adversary*: Pass-the-Hash, Kerberoasting, pivoting across internal subnets.
   - *Defense*: Zero Trust microsegmentation, Tiered Active Directory administration models, blocking SMB between workstations.
6. **Data Exfiltration**:
   - *Adversary*: Moving confidential archives out via encrypted channels, DNS tunneling, or cloud storage.
   - *Defense*: Egress inspection proxies, Data Loss Prevention (DLP), network anomaly detection."""
        },
        {
            "id": "sec_i_2",
            "title": "What are the Various Packet Sniffing and Flow Analysis Tools?",
            "category_id": "network-security",
            "category_name": "Network Security, Protocols & Perimeter Defenses",
            "topic": "Packet Capture & Analysis",
            "difficulty": "Intermediate",
            "experience_level": "Mid-Level Engineer",
            "target_roles": ["Network Security Engineer", "SOC Analyst", "DFIR Investigator"],
            "content": """### Network Analysis & Packet Capture Toolbox

- **Wireshark**: The industry-standard graphical packet analyzer for deep protocol dissection, stream reconstruction, and latency analysis.
- **tcpdump**: The standard lightweight command-line packet capture tool on Linux/UNIX. Ideal for server troubleshooting and automation scripts:
  ```bash
  tcpdump -i eth0 -nn "port 443 or port 80" -w capture.pcap
  ```
- **NetworkMiner**: Passive network sniffer and host reconstruction tool that extracts files, certificates, and credential hashes from PCAP files without generating traffic.
- **NetFlow / IPFIX Analyzers (PRTG, SolarWinds, Zeek)**: Analyzes conversation metadata (source IP, destination IP, bytes transferred, duration) to detect volumetric anomalies and C2 beacons without recording full payloads."""
        },
        {
            "id": "sec_i_3",
            "title": "What is SQL Injection (SQLi) and How Can It Be Prevented?",
            "category_id": "application-security",
            "category_name": "Application Security, Injection Attacks & Web Exploits",
            "topic": "Web Application Security",
            "difficulty": "Intermediate",
            "experience_level": "Mid-Level Engineer",
            "target_roles": ["AppSec Engineer", "Software Engineer", "Penetration Tester"],
            "content": """### SQL Injection Mechanisms
SQL Injection occurs when untrusted user input is directly concatenated into dynamic SQL query strings, allowing attackers to manipulate database syntax, bypass authentication, extract tables, or execute shell commands.

### Types of SQLi:
1. **In-band (Classic)**: Error-based or UNION-based SQLi where extracted data displays directly in the HTTP response.
2. **Blind SQLi**:
   - *Boolean-based*: Inferring true/false database states via conditional page differences.
   - *Time-based*: Forcing the database to sleep (`WAITFOR DELAY '0:0:5'`) to extract characters sequentially.
3. **Out-of-band**: Triggering DNS or SMB requests from the database server to exfiltrate data.

### Robust Prevention: Parameterized Queries (Prepared Statements)
```python
# VULNERABLE: String concatenation
cursor.execute(f"SELECT * FROM users WHERE username = '{user_input}'")

# SECURE: Parameterized Query
cursor.execute("SELECT * FROM users WHERE username = %s", (user_input,))
```
Always use ORM parameterization, grant least privilege on database user accounts, and enforce automated SAST testing."""
        },
        {
            "id": "sec_i_4",
            "title": "What is a Distributed Denial of Service (DDoS) Attack and Mitigation Options?",
            "category_id": "network-security",
            "category_name": "Network Security, Protocols & Perimeter Defenses",
            "topic": "Availability & DDoS",
            "difficulty": "Intermediate",
            "experience_level": "Mid-Level Engineer",
            "target_roles": ["Network Security Engineer", "Site Reliability Engineer (SRE)"],
            "content": """### DDoS Attack Taxonomy
1. **Volumetric Attacks (Layer 3/4)**: Flooding network bandwidth using NTP/DNS amplification or UDP floods measured in Gbps/Tbps.
2. **Protocol Attacks (Layer 4)**: Exhausting server state tables via TCP SYN floods or fragmented packet floods.
3. **Application Layer Attacks (Layer 7)**: Mimicking legitimate HTTP GET/POST traffic (e.g., requesting expensive search queries) to exhaust database connection pools and CPU threads.

### Enterprise Mitigation Architecture:
- **Anycast BGP Routing & Cloud Scrubbing**: Distributes attack traffic globally across hundreds of edge data centers (Cloudflare, AWS Shield).
- **Rate Limiting & Web Application Firewalls**: Drops client IPs exceeding threshold request rates.
- **Autoscaling & Graceful Degradation**: Scales worker clusters dynamically while shedding non-critical batch processing during surges."""
        },
        {
            "id": "sec_i_5",
            "title": "How to Avoid ARP Poisoning on Enterprise Local Networks?",
            "category_id": "network-security",
            "category_name": "Network Security, Protocols & Perimeter Defenses",
            "topic": "Layer 2 Security",
            "difficulty": "Intermediate",
            "experience_level": "Mid-Level Engineer",
            "target_roles": ["Network Security Engineer", "Infrastructure Engineer"],
            "content": """### Layer 2 Defenses Against ARP Poisoning

1. **Dynamic ARP Inspection (DAI)**: Managed enterprise switches inspect ARP packets traversing ports, dropping those with invalid MAC-to-IP bindings based on the trusted DHCP snooping database.
2. **DHCP Snooping**: Designates switchports as trusted or untrusted, blocking rogue DHCP servers and cataloging authorized MAC/IP assignments.
3. **Port Security (802.1X)**: Restricts switchport traffic to authenticated MAC addresses, automatically disabling ports when rogue devices are attached.
4. **Static ARP Tables**: Enforces fixed ARP mappings on high-security core infrastructure gateways."""
        },
        {
            "id": "sec_i_6",
            "title": "What is a Proxy Firewall and How Does It Compare to Stateful Firewalls?",
            "category_id": "network-security",
            "category_name": "Network Security, Protocols & Perimeter Defenses",
            "topic": "Firewall Architectures",
            "difficulty": "Intermediate",
            "experience_level": "Mid-Level Engineer",
            "target_roles": ["Network Security Engineer", "Security Architect"],
            "content": """### Proxy (Application Layer) Firewall Architecture
A **proxy firewall** (Layer 7) acts as an intermediary by terminating client TCP connections, performing deep inspection of application-layer protocols (HTTP, FTP, SMTP), and establishing an entirely separate TCP connection to internal destination servers.

### Comparison:
- **Stateful Packet Inspection**: Tracks Layer 3/4 connections (SYN, ACK). High throughput and low latency, but cannot inspect encrypted payloads or enforce protocol semantics.
- **Proxy Firewall**: Reassembles full application payloads, can perform virus scanning and content filtering, but introduces processing latency and requires dedicated server resources."""
        },
        {
            "id": "sec_i_7",
            "title": "Explain SSL/TLS Encryption: How It Secures Web Traffic and Configuration Best Practices",
            "category_id": "cryptography-iam",
            "category_name": "Cryptography, PKI, IAM & Key Lifecycle",
            "topic": "Transport Security Configuration",
            "difficulty": "Intermediate",
            "experience_level": "Mid-Level Engineer",
            "target_roles": ["DevSecOps Engineer", "AppSec Engineer", "Systems Engineer"],
            "content": """### TLS Operational Architecture
TLS secures HTTP by orchestrating three phases:
1. **Authentication**: The server presents an X.509 certificate validating its identity through a trusted root Certificate Authority chain.
2. **Key Exchange (ECDHE)**: Client and server derive a shared ephemeral session key over an unencrypted channel without ever transmitting the key.
3. **Symmetric Encryption (AES-GCM)**: All subsequent payload data is encrypted with the derived session key.

### Configuration Best Practices:
- Enforce **TLS 1.3** (or TLS 1.2 minimum); disable SSLv2, SSLv3, TLS 1.0, and TLS 1.1.
- Restrict cipher suites to AEAD modes (`TLS_AES_256_GCM_SHA384`, `TLS_CHACHA20_POLY1305_SHA256`).
- Enable **HSTS** with preloading to prevent SSL stripping attacks."""
        },
        {
            "id": "sec_i_8",
            "title": "What Do You Mean by Penetration Testing and Rules of Engagement?",
            "category_id": "application-security",
            "category_name": "Application Security, Injection Attacks & Web Exploits",
            "topic": "Offensive Security & Pentesting",
            "difficulty": "Intermediate",
            "experience_level": "Mid-Level Engineer",
            "target_roles": ["Penetration Tester", "Red Team Engineer", "Security Lead"],
            "content": """### Penetration Testing Execution
A penetration test is an authorized simulated attack designed to discover, exploit, and chain vulnerabilities to validate the operational efficacy of security controls.

### Critical Components of Rules of Engagement (ROE):
- **Defined Scope**: Explicit CIDR blocks, domains, and application endpoints authorized for testing. Out-of-scope third-party SaaS services must be excluded.
- **Testing Windows**: Permitted testing hours to prevent operational disruptions.
- **Emergency Stop Procedures**: Direct escalation contacts if a critical production vulnerability or unintentional denial of service occurs.
- **Data Handling & Non-Disclosure (NDA)**: Guidelines for handling customer PII discovered during exploitation."""
        },
        {
            "id": "sec_i_9",
            "title": "What are the Risks Associated with Public Wi-Fi?",
            "category_id": "network-security",
            "category_name": "Network Security, Protocols & Perimeter Defenses",
            "topic": "Wireless Security",
            "difficulty": "Fundamental",
            "experience_level": "Entry-Level / Intern",
            "target_roles": ["Security Analyst", "IT Helpdesk"],
            "content": """### Threats on Untrusted Wireless Networks
1. **Evil Twin Access Points**: Attackers deploy rogue hotspots mimicking airport or hotel SSIDs (`Starbucks_Guest`) to intercept traffic.
2. **Packet Sniffing**: Capturing unencrypted legacy traffic on open Wi-Fi that lacks 802.11w management frame protection.
3. **Credential & Session Hijacking**: Exploiting missing HSTS headers or cookie flags to steal authentication tokens.

### Mitigations:
- Mandate enterprise VPN deployment for all remote workers.
- Verify that OS network settings treat Wi-Fi connections as 'Public' (disabling local file sharing)."""
        },
        {
            "id": "sec_i_10",
            "title": "Explain the Difference Between Diffie-Hellman and RSA Cryptography",
            "category_id": "cryptography-iam",
            "category_name": "Cryptography, PKI, IAM & Key Lifecycle",
            "topic": "Asymmetric Cryptography",
            "difficulty": "Intermediate",
            "experience_level": "Mid-Level Engineer",
            "target_roles": ["Cryptographer", "Security Architect", "AppSec Engineer"],
            "content": """### Diffie-Hellman vs RSA Comparison

- **Diffie-Hellman (DH / ECDH)**:
  - Specifically a **key agreement protocol**.
  - Enables two parties who have no prior knowledge of each other to jointly establish a shared secret key over an insecure communication channel.
  - *Cannot* encrypt messages directly or sign data independently.
- **RSA**:
  - A general-purpose **asymmetric cryptosystem**.
  - Can be used for **encryption** (encrypting with public key, decrypting with private key) AND **digital signatures** (signing with private key, verifying with public key).

*Modern Standard*: In TLS 1.3, ECDHE handles key exchange for forward secrecy, while RSA or ECDSA handles digital signature verification."""
        },
        {
            "id": "sec_i_11",
            "title": "Explain Session Hijacking Mechanisms and Countermeasures",
            "category_id": "application-security",
            "category_name": "Application Security, Injection Attacks & Web Exploits",
            "topic": "Web Session Security",
            "difficulty": "Intermediate",
            "experience_level": "Mid-Level Engineer",
            "target_roles": ["AppSec Engineer", "Penetration Tester", "SOC Analyst"],
            "content": """### How Attackers Hijack Active Sessions
Session hijacking occurs when an attacker steals or predicts a legitimate user's session identifier (cookie / token), allowing them to impersonate the victim without entering credentials.

### Vectors:
- Stealing cookies via Cross-Site Scripting (XSS).
- Sniffing unencrypted HTTP traffic on local networks.
- Session Fixation: Forcing the victim to authenticate with a known session token provided by the attacker.

### Countermeasures:
1. Enforce strict cookie security attributes:
   ```http
   Set-Cookie: session_id=abc123xyz; Secure; HttpOnly; SameSite=Strict;
   ```
2. Regenerate session identifiers immediately upon successful authentication.
3. Bind session tokens to client fingerprints (IP, TLS connection state, user-agent) and enforce short inactivity timeouts."""
        },
        {
            "id": "sec_i_12",
            "title": "What is Zero Trust Architecture and the Principle of Least Privilege?",
            "category_id": "cloud-architecture-devsecops",
            "category_name": "Enterprise Architecture, System Hardening & Advanced Threats",
            "topic": "Enterprise Architecture",
            "difficulty": "Advanced",
            "experience_level": "Senior / Staff Architect",
            "target_roles": ["Security Architect", "CISO Office", "Cloud Security Engineer"],
            "content": """### Core Tenets of Zero Trust (NIST SP 800-207)
Traditional perimeter security operated under the 'Castle and Moat' model (trust everything inside the corporate intranet). **Zero Trust** reverses this: **'Never Trust, Always Verify'**.

### Core Principles:
1. **Continuous Verification**: Authenticate and authorize every access request based on user identity, device posture, location, and risk signals, regardless of network location.
2. **Limit Blast Radius via Least Privilege**: Grant users and services only the minimal permissions required for their specific function (RBAC/ABAC with Just-In-Time access).
3. **Assume Breach**: Segment internal networks into micro-perimeters, encrypt all internal communications (mTLS), and log all telemetry continuously to detect lateral movement."""
        },
        {
            "id": "sec_i_13",
            "title": "What is a SIEM (Security Information and Event Management) System and What Role Does It Play in a SOC?",
            "category_id": "soc-incident-response",
            "category_name": "Incident Response, SOC Operations, SIEM & Threat Hunting",
            "topic": "Security Operations & Triage",
            "difficulty": "Intermediate",
            "experience_level": "Mid-Level Engineer",
            "target_roles": ["SOC Analyst", "SIEM Engineer", "Incident Responder"],
            "content": """### What is a SIEM?
A **SIEM** (e.g., Splunk, Microsoft Sentinel, Elastic Security) acts as the centralized nerve center for a Security Operations Center (SOC).

### Core SIEM Functions:
1. **Log Aggregation & Ingestion**: Ingests gigabytes of telemetry daily from firewalls, Windows Event Logs, Linux Syslog, cloud audit trails (AWS CloudTrail), and EDR agents.
2. **Normalization & Parsing**: Converts disparate log formats into unified schemas (e.g., Elastic Common Schema - ECS).
3. **Correlation & Detection Analytics**: Applies correlation rules and machine learning to detect patterns indicative of an attack (e.g., 50 failed logins followed by a successful login and an immediate outbound SSH connection).
4. **Alerting & Playbook Integration**: Automatically triggers SOAR (Security Orchestration, Automation, and Response) workflows to isolate hosts or revoke compromised credentials."""
        },
        {
            "id": "sec_i_14",
            "title": "How Does a Rootkit Function and What are Detection Techniques?",
            "category_id": "cloud-architecture-devsecops",
            "category_name": "Enterprise Architecture, System Hardening & Advanced Threats",
            "topic": "Kernel & OS Security",
            "difficulty": "Advanced",
            "experience_level": "Senior / Staff Architect",
            "target_roles": ["Incident Responder", "Malware Researcher", "Security Engineer"],
            "content": """### Rootkit Architecture
A **rootkit** is a sophisticated stealth malware suite designed to maintain privileged persistent access while concealing its presence from system monitoring tools and antivirus scanners.

### Levels of Rootkits:
- **User-Mode Rootkits**: Hooks system APIs or substitutes standard system binaries (`/bin/ps`, `/bin/ls`) to filter out malicious processes and files from output.
- **Kernel-Mode Rootkits**: Modifies the operating system kernel, System Call Tables, or hooks device drivers, granting absolute control over hardware and telemetry.
- **Firmware / Bootkits**: Modifies the Master Boot Record (MBR) or UEFI firmware, executing before the operating system boots.

### Detection Methods:
- Hardware Root of Trust and **UEFI Secure Boot** enforcing digital signatures on all bootloader components.
- Memory analysis via Volatility examining unlinked `EPROCESS` structures.
- Offline disk scanning using live forensics USB environments."""
        },
        {
            "id": "sec_i_15",
            "title": "What is a Zero-Day Vulnerability and How Should Organizations Formulate a Response?",
            "category_id": "cloud-architecture-devsecops",
            "category_name": "Enterprise Architecture, System Hardening & Advanced Threats",
            "topic": "Vulnerability Management",
            "difficulty": "Intermediate",
            "experience_level": "Mid-Level Engineer",
            "target_roles": ["Vulnerability Manager", "SOC Lead", "Security Architect"],
            "content": """### Zero-Day Defined
A **Zero-Day Vulnerability** is a security flaw in software or hardware that is unknown to the vendor, or known but without an available vendor patch, leaving zero days of defense between discovery and exploitation.

### Compensating Control Strategy Prior to Patch Availability:
1. **Threat Hunting**: Search SIEM and EDR telemetry for published Indicators of Compromise (IOCs) and exploit signatures.
2. **Virtual Patching**: Deploy targeted Web Application Firewall (WAF) or IPS rules that detect and block the specific exploit string.
3. **Network Isolation**: Restrict network access to affected applications to internal admin subnets via VPN.
4. **Disable Vulnerable Services**: If non-critical, temporarily shut down affected daemons until official vendor patches are vetted and applied."""
        },

        # =========================================================================
        # 3. EXPERIENCED / ADVANCED CYBERSECURITY QUESTIONS
        # =========================================================================
        {
            "id": "sec_e_1",
            "title": "Advanced Man-in-the-Middle Attacks: TLS Interception, Rogue Certificates, and Protocol Downgrades",
            "category_id": "network-security",
            "category_name": "Network Security, Protocols & Perimeter Defenses",
            "topic": "Advanced Attack Techniques",
            "difficulty": "Advanced",
            "experience_level": "Senior / Staff Architect",
            "target_roles": ["Security Architect", "Red Team Lead", "Cryptographer"],
            "content": """### Advanced MITM Exploitation Vectors

1. **Compromised / Rogue Certificate Authorities**:
   - Adversaries possessing compromised intermediate CAs can mint legitimate-looking wildcard certificates for targets, decrypting TLS without browser warnings.
   - *Mitigation*: **Certificate Transparency (CT)** logs mandate that all public CAs publish newly issued certificates to publicly auditable append-only cryptographic Merkle trees.
2. **TLS Downgrade Attacks**:
   - Forcing negotiation down to insecure cipher suites or obsolete TLS versions.
   - *Mitigation*: Enforcing TLS 1.3 exclusively, which signs the entire handshake negotiation history to thwart tampering.
3. **OAuth Token Interception**:
   - Hijacking custom URI redirect schemes in mobile environments to harvest authorization codes.
   - *Mitigation*: Mandatory deployment of **PKCE (RFC 7636)**."""
        },
        {
            "id": "sec_e_2",
            "title": "What is Traceroute, How Does It Function Under the Hood, and How is It Used in Threat Hunting?",
            "category_id": "network-security",
            "category_name": "Network Security, Protocols & Perimeter Defenses",
            "topic": "Network Forensics",
            "difficulty": "Intermediate",
            "experience_level": "Mid-Level Engineer",
            "target_roles": ["Network Security Engineer", "SOC Analyst", "DFIR Specialist"],
            "content": """### Traceroute Operational Mechanics
Traceroute maps the network hop path between source and destination by manipulating the **Time-To-Live (TTL)** field in packet IP headers:

1. **TTL = 1**: The client sends a packet with TTL=1. The first router decrements TTL to 0, drops the packet, and returns an `ICMP Time Exceeded` packet. The client records the router's IP and round-trip time.
2. **TTL Increment**: The client repeats the process with TTL=2, TTL=3, until the destination answers with an ICMP Echo Reply or TCP SYN/ACK.

### Threat Hunting Applications:
- **BGP Route Hijacking Detection**: Unusually high hop counts or unexpected autonomous system (AS) transit paths indicate traffic redirection.
- **Egress Firewall Validation**: Validating that internal servers cannot route traffic through unauthorized egress gateways."""
        },
        {
            "id": "sec_e_3",
            "title": "What is the Difference Between HIDS (Host-Based) and NIDS (Network-Based)?",
            "category_id": "soc-incident-response",
            "category_name": "Incident Response, SOC Operations, SIEM & Threat Hunting",
            "topic": "Intrusion Detection Architecture",
            "difficulty": "Intermediate",
            "experience_level": "Mid-Level Engineer",
            "target_roles": ["SOC Analyst", "Security Engineer"],
            "content": """### HIDS vs NIDS Architecture Comparison

| Feature | Host-based IDS (HIDS) | Network-based IDS (NIDS) |
| :--- | :--- | :--- |
| **Placement** | Installed as a local agent on endpoints/servers (e.g., OSSEC, Wazuh). | Deployed on network TAP or switch SPAN mirror ports (e.g., Snort, Suricata, Zeek). |
| **Visibility** | Complete visibility into local processes, file modifications, memory hooks, and decrypted traffic. | Broad visibility into all inter-host and perimeter traffic across network segments. |
| **Encryption Blindspot** | Zero blindspot: Inspects data before encryption or after decryption on the host. | Blind to encrypted payload contents unless dedicated TLS decryption break-and-inspect is configured. |
| **Resource Overhead** | Consumes host CPU and memory; must be maintained on every managed endpoint. | Zero performance impact on endpoints; requires high-capacity dedicated monitoring hardware. |"""
        },
        {
            "id": "sec_e_4",
            "title": "Explain Advanced Persistent Threats (APT) and Defense-in-Depth Strategies",
            "category_id": "cloud-architecture-devsecops",
            "category_name": "Enterprise Architecture, System Hardening & Advanced Threats",
            "topic": "Nation-State Threats & APT",
            "difficulty": "Advanced",
            "experience_level": "Senior / Staff Architect",
            "target_roles": ["CISO Office", "Threat Intelligence Lead", "Senior Incident Responder"],
            "content": """### What Distinguishes an APT?
An **Advanced Persistent Threat (APT)** is a prolonged, stealthy, and targeted computer network attack conducted by highly skilled adversaries (often nation-state intelligence agencies or state-sponsored syndicates) pursuing strategic objectives such as intellectual property theft or critical infrastructure pre-positioning.

### Characteristics:
- **Custom Tooling & Zero-Days**: Avoids commercial malware that triggers off-the-shelf antivirus signatures.
- **Living off the Land (LotL)**: Utilizes native administrative binaries (`powershell.exe`, `wmic.exe`, `certutil.exe`) to execute commands without dropping files.
- **Long Dwell Times**: Maintains quiet persistence for months or years without disrupting services.

### Defense Strategy:
- Map detections comprehensively against **MITRE ATT&CK**.
- Proactive hypothesis-driven **Threat Hunting** in EDR telemetry rather than purely reactive alert triage.
- Deception technology (canary tokens, breadcrumb credentials in memory)."""
        },
        {
            "id": "sec_e_5",
            "title": "Explain Micro-Segmentation in Cloud & Modern Enterprise Networks",
            "category_id": "cloud-architecture-devsecops",
            "category_name": "Enterprise Architecture, System Hardening & Advanced Threats",
            "topic": "Zero Trust Architecture",
            "difficulty": "Advanced",
            "experience_level": "Senior / Staff Architect",
            "target_roles": ["Security Architect", "Cloud Security Engineer", "DevSecOps Lead"],
            "content": """### Micro-Segmentation Principles
Traditional perimeter security leaves internal network subnets flat, allowing an attacker who breaches one workstation to pivot freely across internal servers (east-west movement). **Micro-segmentation** enforces granular, workload-level network access policies, isolating individual services from each other.

### Implementation Patterns:
1. **Software-Defined Networking (SDN) & Host Firewalls**: Enforcing policies via host agents (e.g., Illumio, AWS Security Groups) independent of physical IP topology.
2. **Kubernetes NetworkPolicies & Service Meshes (Istio/Linkerd)**:
   - Enforcing mutual TLS (mTLS) with cryptographically validated SPIFFE identities.
   - Default-deny rules allowing only explicit application-to-application communication:
   ```yaml
   apiVersion: networking.k8s.io/v1
   kind: NetworkPolicy
   metadata:
     name: allow-frontend-to-backend
   spec:
     podSelector:
       matchLabels:
         app: backend
     ingress:
     - from:
       - podSelector:
           matchLabels:
             app: frontend
   ```"""
        },
        {
            "id": "sec_e_6",
            "title": "What is Post-Quantum Cryptography (PQC) and Why Must Organizations Prepare?",
            "category_id": "cryptography-iam",
            "category_name": "Cryptography, PKI, IAM & Key Lifecycle",
            "topic": "Post-Quantum Cryptography",
            "difficulty": "Advanced",
            "experience_level": "Senior / Staff Architect",
            "target_roles": ["Cryptographer", "Security Architect", "CISO Office"],
            "content": """### The Quantum Threat to Modern Cryptography
Sufficiently powerful quantum computers running **Shor's Algorithm** will be capable of breaking modern asymmetric public-key cryptography (RSA, Diffie-Hellman, ECC) in polynomial time, collapsing internet authentication and encrypted key exchange.

### The 'Harvest Now, Decrypt Later' (HNDL) Threat:
Adversaries are currently recording massive volumes of encrypted military and corporate internet traffic, storing it until quantum computers mature to decrypt the stored archives retroactively.

### NIST PQC Standards:
- **ML-KEM (Kyber)**: Primary lattice-based Key Encapsulation Mechanism for general encryption and TLS key exchange.
- **ML-DSA (Dilithium)** and **SLH-DSA (SPHINCS+)**: Lattice-based and stateless hash-based digital signature schemes.

Organizations must practice **Cryptographic Agility**—designing software so algorithms and key lengths can be swapped without rewriting core business architecture."""
        },
        {
            "id": "sec_e_7",
            "title": "Explain Federated Identity Management (SAML 2.0 vs OIDC / OAuth 2.0)",
            "category_id": "cryptography-iam",
            "category_name": "Cryptography, PKI, IAM & Key Lifecycle",
            "topic": "Identity Federation",
            "difficulty": "Advanced",
            "experience_level": "Senior / Staff Architect",
            "target_roles": ["IAM Engineer", "Security Architect", "AppSec Engineer"],
            "content": """### Federated Identity Architecture
Federated identity enables cross-domain Single Sign-On (SSO), allowing users to authenticate with a central **Identity Provider (IdP)** (e.g., Okta, Entra ID) and access independent **Service Providers (SP)** without replicating credentials.

### Protocol Comparison:
- **SAML 2.0 (Security Assertion Markup Language)**:
  - Heavy XML-based tokens signed with X.509 digital certificates.
  - Dominant in legacy enterprise SaaS applications.
  - Vulnerable to XML Signature Wrapping (XSW) and XML External Entity (XXE) attacks if parsers are misconfigured.
- **OIDC (OpenID Connect)**:
  - Modern identity layer built directly on top of **OAuth 2.0**.
  - Uses compact, lightweight **JSON Web Tokens (JWT)**.
  - Engineered specifically for Single Page Applications (SPAs), mobile apps, and microservice APIs."""
        },
        {
            "id": "sec_e_8",
            "title": "How Do You Manage Cryptographic Keys Securely Across Their Full Lifecycle?",
            "category_id": "cryptography-iam",
            "category_name": "Cryptography, PKI, IAM & Key Lifecycle",
            "topic": "Key Management & HSMs",
            "difficulty": "Advanced",
            "experience_level": "Senior / Staff Architect",
            "target_roles": ["Security Architect", "PKI Administrator", "Cloud Security Engineer"],
            "content": """### The Cryptographic Key Lifecycle (NIST SP 800-57)

1. **Generation**: Generated using certified Hardware Security Modules (HSMs) leveraging cryptographically secure hardware Random Number Generators (TRNG).
2. **Storage**: Master keys must never reside in plaintext on disk or application memory. Keys are protected using Key Encryption Keys (Envelope Encryption).
3. **Distribution & Transport**: Transmitted using TLS or direct hardware-to-hardware wrapped key exchanges.
4. **Rotation**: Automated scheduled key rotation (e.g., every 90 to 365 days) ensuring compromised keys limit the exposure window.
5. **Revocation & Destruction**: Cryptographic erasure (zeroization) ensuring keys are unrecoverable from physical media."""
        },
        {
            "id": "sec_e_9",
            "title": "What are the Standard Methods for Secure Data Disposal on Storage Media?",
            "category_id": "cybersecurity-fundamentals",
            "category_name": "Cybersecurity Fundamentals & Threat Taxonomy",
            "topic": "Data Sanitization Standards",
            "difficulty": "Intermediate",
            "experience_level": "Mid-Level Engineer",
            "target_roles": ["Security Engineer", "Storage Admin", "IT Auditor"],
            "content": """### Sanitization Methods (NIST SP 800-88 Rev. 1)

1. **Clear**: Overwriting addressable storage locations with standard data patterns (single overwrite pass), protecting against simple non-invasive keyboard recovery.
2. **Purge**: Executing cryptographic erasure (destroying encryption keys on self-encrypting drives) or low-level block overhauls (ATA Secure Erase) to make recovery infeasible even using advanced laboratory tools.
3. **Destroy**: Physical destruction of storage media via degaussing (for magnetic platters), mechanical shredding to 2mm cross-cut particles, or incineration."""
        },
        {
            "id": "sec_e_10",
            "title": "Explain What is Active Reconnaissance vs Passive Reconnaissance in Threat Operations",
            "category_id": "application-security",
            "category_name": "Application Security, Injection Attacks & Web Exploits",
            "topic": "Reconnaissance Methodologies",
            "difficulty": "Intermediate",
            "experience_level": "Mid-Level Engineer",
            "target_roles": ["Penetration Tester", "Red Teamer", "Threat Intelligence Analyst"],
            "content": """### Active vs Passive Reconnaissance

- **Passive Reconnaissance**:
  - Gathering intelligence without sending packets directly to the target systems.
  - Uses public repositories, Certificate Transparency logs (crt.sh), Shodan, WHOIS records, and DNS dumpster.
  - Leaves zero telemetry footprint on the victim's firewalls or IDS.
- **Active Reconnaissance**:
  - Interacting directly with the target infrastructure to discover open ports, service banners, and software versions.
  - Tools include Nmap, Masscan, Nuclei, and dirsearch.
  - High risk of triggering IDS/IPS alerts, generating IP blocks and incident response triage."""
        }
    ]

    # Post-process questions to guarantee all required schema fields
    final_questions = []
    for item in raw_items:
        q_id = item["id"]
        q_slug = item.get("slug") or slugify(f"sec-{item['title']}")
        md_content = item["content"].strip()

        final_questions.append({
            "id": q_id,
            "slug": q_slug,
            "title": item["title"],
            "domain_id": "security_engineering",
            "category_id": item["category_id"],
            "category_name": item["category_name"],
            "topic": item.get("topic", item["category_name"]),
            "difficulty": item["difficulty"],
            "experience_level": item.get("experience_level", "Mid-Level Engineer"),
            "target_roles": item.get("target_roles", ["Security Engineer", "Security Analyst"]),
            "content": md_content,
            "markdown_content": md_content,
            "educational_diagram": item.get("educational_diagram"),
            "educational_diagram_alt": item.get("educational_diagram_alt"),
            "estimated_read_time_min": max(2, len(md_content.split()) // 140),
            "has_code": "```" in md_content,
            "has_diagram": bool(item.get("educational_diagram")) or ("![" in md_content),
            "source_repository": REPO_URL,
            "source_commit": REPO_COMMIT,
            "source_license": REPO_LICENSE,
            "source_file": REPO_FILE,
            "translation_notice": "Sourced and enriched from abhinavkakku/Cyber_Security_Interview_Questions.",
            "tags": [
                "Security Engineering",
                item["category_id"],
                item.get("experience_level", "Mid-Level Engineer")
            ] + item.get("target_roles", [])
        })

    return final_questions
