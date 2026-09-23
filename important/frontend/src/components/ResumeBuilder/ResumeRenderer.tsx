import React from 'react';
import type { StructuredResumeData, ResumeSettings, ResumeProfileData } from '../../api/client';
import {
  getLanguageProficiencyLabel,
  getLocalizedSectionTitle,
  getLocalizedPresentLabel,
  getLocalizedDegreeConnector,
  getLocalizedHonorsLabel,
  DEFAULT_SECTION_TITLES_BY_LANG,
} from './resumeLocalization';
import './ResumeRenderer.css';

export const DEFAULT_SECTION_TITLES = DEFAULT_SECTION_TITLES_BY_LANG.en;

export function resolveSectionTitle(
  sectionKey: string,
  customTitles?: Record<string, string>,
  lang: string = 'en'
): string {
  return getLocalizedSectionTitle(sectionKey, lang, customTitles?.[sectionKey]);
}

interface ResumeRendererProps {
  data: StructuredResumeData;
  settings: ResumeSettings;
}

export const ResumeRenderer: React.FC<ResumeRendererProps> = ({ data, settings }) => {
  const profile: Partial<ResumeProfileData> = data?.profile || {};
  const experience = data?.experience || [];
  const education = data?.education || [];
  const skills = data?.skills || [];
  const projects = data?.projects || [];
  const certifications = data?.certifications || [];
  const languages = data?.languages || [];
  const custom_sections = data?.custom_sections || [];

  const lang = (settings.language || 'en').toLowerCase();
  const secTitles = settings.section_titles || {};
  const visibility = settings.section_visibility || {};
  const order = settings.section_order || [
    'summary',
    'experience',
    'education',
    'skills',
    'projects',
    'certifications',
    'languages',
    'custom_sections',
  ];

  const secTitle = (key: string) => resolveSectionTitle(key, secTitles, lang);

  return (
    <div
      className={`resume-paper resume-document template-${settings.template || 'modern'}`}
      style={
        {
          '--resume-accent': settings.theme_color || '#2563eb',
          '--primary-color': settings.theme_color || '#2563eb',
          '--font-family': settings.font_family || 'Inter',
          '--font-size-base': `${settings.font_size || '10.5'}pt`,
        } as React.CSSProperties
      }
    >
      {/* Header / Profile Section */}
      {visibility.profile !== false && (
        <header className="resume-header">
          <h1 className="candidate-name">
            {profile.full_name || (data as any)?.name || (data as any)?.full_name || 'Your Full Name'}
          </h1>
          {profile.headline && <div className="candidate-headline">{profile.headline}</div>}
          <div className="contact-info-row">
            {profile.email && <span className="contact-item">{profile.email}</span>}
            {profile.phone && <span className="contact-item">{profile.phone}</span>}
            {profile.location && <span className="contact-item">{profile.location}</span>}
            {profile.linkedin && (
              <span className="contact-item">
                <a href={profile.linkedin} target="_blank" rel="noreferrer">LinkedIn</a>
              </span>
            )}
            {profile.github && (
              <span className="contact-item">
                <a href={profile.github} target="_blank" rel="noreferrer">GitHub</a>
              </span>
            )}
            {profile.website && (
              <span className="contact-item">
                <a href={profile.website} target="_blank" rel="noreferrer">Portfolio</a>
              </span>
            )}
          </div>
        </header>
      )}

      {/* Dynamic Sections via section_order */}
      <div className="resume-body">
        {order.map((sectionKey) => {
          if (visibility[sectionKey] === false) return null;

          switch (sectionKey) {
            case 'summary':
              return profile.summary ? (
                <section key="summary" className="resume-section section-summary">
                  <h2 className="section-title">{secTitle('summary')}</h2>
                  <p className="summary-text">{profile.summary}</p>
                </section>
              ) : null;

            case 'skills':
              return skills && skills.length > 0 ? (
                <section key="skills" className="resume-section section-skills">
                  <h2 className="section-title">{secTitle('skills')}</h2>
                  <div className="skills-grid">
                    {skills.map((skill) => (
                      <div key={skill.id} className="skill-item">
                        <span className="skill-name">{skill.name}</span>
                      </div>
                    ))}
                  </div>
                </section>
              ) : null;

            case 'experience':
              return experience && experience.length > 0 ? (
                <section key="experience" className="resume-section section-experience">
                  <h2 className="section-title">{secTitle('experience')}</h2>
                  <div className="experience-list">
                    {experience.map((exp) => (
                      <div key={exp.id} className="exp-item">
                        <div className="item-header-row">
                          <div className="item-title-col">
                            <span className="item-title">{exp.title}</span>
                            {exp.company && <span className="item-company"> — {exp.company}</span>}
                            {exp.location && <span className="item-location"> ({exp.location})</span>}
                          </div>
                          <div className="item-date">
                            {exp.start_date || exp.end_date
                              ? `${exp.start_date} – ${exp.end_date || (exp.is_current ? getLocalizedPresentLabel(lang) : '')}`
                              : ''}
                          </div>
                        </div>
                        {exp.description && <p className="item-description">{exp.description}</p>}
                        {exp.highlights && exp.highlights.length > 0 && (
                          <ul className="item-bullets">
                            {exp.highlights.map((h, i) => (
                              <li key={i}>{h}</li>
                            ))}
                          </ul>
                        )}
                      </div>
                    ))}
                  </div>
                </section>
              ) : null;

            case 'education':
              return education && education.length > 0 ? (
                <section key="education" className="resume-section section-education">
                  <h2 className="section-title">{secTitle('education')}</h2>
                  <div className="education-list">
                    {education.map((edu) => (
                      <div key={edu.id} className="edu-item">
                        <div className="item-header-row">
                          <div className="item-title-col">
                            <span className="item-title">
                              {edu.degree} {edu.field ? `${getLocalizedDegreeConnector(lang)} ${edu.field}` : ''}
                            </span>
                            {edu.institution && (
                              <span className="item-company"> — {edu.institution}</span>
                            )}
                          </div>
                          <div className="item-date">
                            {edu.start_date || edu.end_date ? `${edu.start_date} – ${edu.end_date}` : ''}
                          </div>
                        </div>
                        {edu.gpa && <div className="edu-gpa">{getLocalizedHonorsLabel(lang)} {edu.gpa}</div>}
                        {edu.description && <p className="item-description">{edu.description}</p>}
                      </div>
                    ))}
                  </div>
                </section>
              ) : null;

            case 'projects':
              return projects && projects.length > 0 ? (
                <section key="projects" className="resume-section section-projects">
                  <h2 className="section-title">{secTitle('projects')}</h2>
                  <div className="projects-list">
                    {projects.map((proj) => (
                      <div key={proj.id} className="project-item">
                        <div className="item-header-row">
                          <div className="item-title-col">
                            <span className="item-title">{proj.name}</span>
                            {proj.technologies && (
                              <span className="project-tech"> ({proj.technologies})</span>
                            )}
                          </div>
                          <div className="item-date">
                            {proj.start_date || proj.end_date ? `${proj.start_date} – ${proj.end_date}` : ''}
                          </div>
                        </div>
                        {proj.url && (
                          <div className="project-url">
                            <a href={proj.url} target="_blank" rel="noreferrer">
                              {proj.url}
                            </a>
                          </div>
                        )}
                        {proj.description && <p className="item-description">{proj.description}</p>}
                      </div>
                    ))}
                  </div>
                </section>
              ) : null;

            case 'certifications':
              return certifications && certifications.length > 0 ? (
                <section key="certifications" className="resume-section section-certifications">
                  <h2 className="section-title">{secTitle('certifications')}</h2>
                  <ul className="cert-list item-bullets">
                    {certifications.map((cert) => (
                      <li key={cert.id}>
                        <strong>{cert.name}</strong>
                        {cert.issuer && ` — ${cert.issuer}`}
                        {cert.issue_date && ` (${cert.issue_date})`}
                      </li>
                    ))}
                  </ul>
                </section>
              ) : null;

            case 'languages':
              return languages && languages.length > 0 ? (
                <section key="languages" className="resume-section section-languages">
                  <h2 className="section-title">{secTitle('languages')}</h2>
                  <div className="languages-pills">
                    {languages.map((l) => {
                      const profLabel = getLanguageProficiencyLabel(l.proficiency, lang);
                      return (
                        <span key={l.id} className="lang-tag">
                          <strong>{l.language}</strong>
                          {profLabel ? ` (${profLabel})` : null}
                        </span>
                      );
                    })}
                  </div>
                </section>
              ) : null;

            case 'custom_sections':
              return custom_sections && custom_sections.length > 0 ? (
                <div key="custom_sections">
                  {custom_sections.map((cSec) => (
                    <section key={cSec.id} className="resume-section section-custom">
                      <h2 className="section-title">{cSec.title || secTitle('custom_sections')}</h2>
                      <ul className="item-bullets">
                        {cSec.items.map((it, idx) => (
                          <li key={idx}>{it}</li>
                        ))}
                      </ul>
                    </section>
                  ))}
                </div>
              ) : null;


            default:
              return null;
          }
        })}
      </div>
    </div>
  );
};
