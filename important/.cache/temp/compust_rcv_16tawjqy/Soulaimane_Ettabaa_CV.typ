// Import the rendercv function and all the refactored components
#import "@preview/rendercv:0.3.0": *

// Apply the rendercv template with custom configuration
#show: rendercv.with(
  name: "Soulaimane Ettabaa",
  title: "Soulaimane Ettabaa - CV",
  footer: context { [#emph[Soulaimane Ettabaa -- #str(here().page())\/#str(counter(page).final().first())]] },
  top-note: [ #emph[Dernière mise à jour Oct 2026] ],
  locale-catalog-language: "fr",
  text-direction: ltr,
  page-size: "a4",
  page-top-margin: 0.7in,
  page-bottom-margin: 0.7in,
  page-left-margin: 0.7in,
  page-right-margin: 0.7in,
  page-show-footer: true,
  page-show-top-note: true,
  colors-body: rgb(0, 0, 0),
  colors-name: rgb(30, 64, 175),
  colors-headline: rgb(0, 79, 144),
  colors-connections: rgb(0, 79, 144),
  colors-section-titles: rgb(30, 64, 175),
  colors-links: rgb(0, 79, 144),
  colors-footer: rgb(128, 128, 128),
  colors-top-note: rgb(128, 128, 128),
  typography-line-spacing: 0.6em,
  typography-alignment: "justified",
  typography-date-and-location-column-alignment: right,
  typography-font-family-body: "Source Sans 3",
  typography-font-family-name: "Source Sans 3",
  typography-font-family-headline: "Source Sans 3",
  typography-font-family-connections: "Source Sans 3",
  typography-font-family-section-titles: "Source Sans 3",
  typography-font-size-body: 10pt,
  typography-font-size-name: 30pt,
  typography-font-size-headline: 10pt,
  typography-font-size-connections: 10pt,
  typography-font-size-section-titles: 1.4em,
  typography-small-caps-name: false,
  typography-small-caps-headline: false,
  typography-small-caps-connections: false,
  typography-small-caps-section-titles: false,
  typography-bold-name: true,
  typography-bold-headline: false,
  typography-bold-connections: false,
  typography-bold-section-titles: true,
  links-underline: false,
  links-show-external-link-icon: false,
  header-alignment: center,
  header-photo-width: 3.5cm,
  header-space-below-name: 0.7cm,
  header-space-below-headline: 0.7cm,
  header-space-below-connections: 0.7cm,
  header-connections-hyperlink: true,
  header-connections-show-icons: true,
  header-connections-display-urls-instead-of-usernames: false,
  header-connections-separator: "",
  header-connections-space-between-connections: 0.5cm,
  section-titles-type: "with_partial_line",
  section-titles-line-thickness: 0.5pt,
  section-titles-space-above: 0.5cm,
  section-titles-space-below: 0.3cm,
  sections-allow-page-break: true,
  sections-space-between-text-based-entries: 0.3em,
  sections-space-between-regular-entries: 1.2em,
  entries-date-and-location-width: 4.15cm,
  entries-side-space: 0.2cm,
  entries-space-between-columns: 0.1cm,
  entries-allow-page-break: false,
  entries-short-second-row: true,
  entries-degree-width: 1cm,
  entries-summary-space-left: 0cm,
  entries-summary-space-above: 0cm,
  entries-highlights-bullet:  "•" ,
  entries-highlights-nested-bullet:  "•" ,
  entries-highlights-space-left: 0.15cm,
  entries-highlights-space-above: 0cm,
  entries-highlights-space-between-items: 0cm,
  entries-highlights-space-between-bullet-and-text: 0.5em,
  date: datetime(
    year: 2026,
    month: 10,
    day: 4,
  ),
)


= Soulaimane Ettabaa

  #headline([Ingénieur Sécurité & Systèmes])

#connections(
  [#connection-with-icon("location-dot")[Paris, France]],
  [#link("mailto:soulaimane@example.com", icon: false, if-underline: false, if-color: false)[#connection-with-icon("envelope")[soulaimane\@example.com]]],
  [#link("tel:+33-6-12-34-56-78", icon: false, if-underline: false, if-color: false)[#connection-with-icon("phone")[06 12 34 56 78]]],
  [#link("https://linkedin.com/in/soulaimane", icon: false, if-underline: false, if-color: false)[#connection-with-icon("linkedin")[soulaimane]]],
  [#link("https://github.com/soulaimane", icon: false, if-underline: false, if-color: false)[#connection-with-icon("github")[soulaimane]]],
)


== Profil Professionnel

Élève ingénieur en Sécurité des SI passionné par le DevSecOps.

== Expérience Professionnelle

#regular-entry(
  [
    #strong[CyberSec SAS], Analyste SOC

    - Analyse d'incidents de sécurité.

    - Détection des menaces avec Wazuh et YARA.

    - Automatisation des workflows en Python.

  ],
  [
    Paris, France

    Jan 2023 – Jan 2024

  ],
)

#regular-entry(
  [
    #strong[CloudTech], Lead DevSecOps

    - Gestion des clusters Kubernetes sécurisés.

    - Mise en place de CI\/CD sécurisé.

  ],
  [
    Remote

    Fév 2024 – présent

  ],
)

== Formation & Diplômes

#education-entry(
  [
    #strong[ENSIMAG], Cybersécurité

    - GPA \/ Honors: Mention Très Bien

    - Spécialisation en sécurité des architectures distribuées.

  ],
  [
    Grenoble, France

    Sep 2022 – Juin 2025

  ],
  degree-column: [
    #strong[Diplôme d'Ingénieur]
  ],
)

== Compétences

#strong[Languages:] Python, C++

#strong[Systems:] Linux

#strong[DevOps:] Docker

== Projets Réalisés

#regular-entry(
  [
    #strong[#link("https://github.com/soulaimane/audit-scanner")[AuditScanner]]

    #summary[Python, Django, PostgreSQL]

    - Scanner de vulnérabilités statique pour code source.

  ],
  [
    Jan 2023 – Jan 2024

  ],
)

== Certifications

#regular-entry(
  [
    #strong[Security+]

    #summary[CompTIA]

  ],
  [
    Mai 2023

  ],
)

== Langues

#strong[Langues:] Français (Langue maternelle), Anglais (Courant)

== Centres d'intérêt

CTF \/ HackTheBox

Open Source Contribution
