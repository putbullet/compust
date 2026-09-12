import React from 'react';
import type { StructuredResumeData, ResumeSettings } from '../../api/client';
import './ResumeRenderer.css';

interface ResumeRendererProps {
  data: StructuredResumeData;
  settings: ResumeSettings;
}

export const ResumeRenderer: React.FC<ResumeRendererProps> = ({ data, settings }) => {
  const { profile, experience, education, skills, projects, certifications, languages, custom_sections } = data;
  const { template, theme_color, font_size, section_order, section_visibility } = settings;

  const isVisible = (sectionKey: string) => section_visibility[sectionKey] !== false;

  const baseFontSize = `${font_size || '10.5'}pt`;

  return (
    <div
      className={`resume-paper template-${template}`}
      style={{
        fontSize: baseFontSize,
        // CSS variables for dynamic styling
        ['--resume-accent' as any]: theme_color || '#2563eb',
      }}
    >
      {/* Profile Header */}
      {isVisible('profile') && (
        <header className="resume-header">
          <h1 className="resume-name">{profile.full_name || 'Your Full Name'}</h1>
          {profile.headline && <div className="resume-headline">{profile.headline}</div>}

          <div className="resume-contact-row">
            {profile.email && (
              <span className="contact-item">
                <span className="contact-bullet">•</span> {profile.email}
              </span>
            )}
            {profile.phone && (
              <span className="contact-item">
                <span className="contact-bullet">•</span> {profile.phone}
              </span>
            )}
            {profile.location && (
              <span className="contact-item">
                <span className="contact-bullet">•</span> {profile.location}
              </span>
            )}
            {profile.linkedin && (
              <span className="contact-item">
                <span className="contact-bullet">•</span> {profile.linkedin.replace(/^https?:\/\/(www\.)?linkedin\.com\/in\//, 'in/')}
              </span>
            )}
            {profile.github && (
              <span className="contact-item">
                <span className="contact-bullet">•</span> {profile.github.replace(/^https?:\/\/(www\.)?github\.com\//, 'github/')}
              </span>
            )}
            {profile.website && (
              <span className="contact-item">
                <span className="contact-bullet">•</span> {profile.website.replace(/^https?:\/\//, '')}
              </span>
            )}
          </div>
          <div className="header-divider" />
        </header>
      )}

      {/* Dynamic Sections by Order */}
      <div className="resume-body">
        {section_order.map((sectionKey) => {
          if (!isVisible(sectionKey)) return null;

          switch (sectionKey) {
            case 'summary':
              return profile.summary ? (
                <section key="summary" className="resume-section section-summary">
                  <h2 className="section-title">Professional Summary</h2>
                  <p className="summary-text">{profile.summary}</p>
                </section>
              ) : null;

            case 'skills':
              return skills && skills.length > 0 ? (
                <section key="skills" className="resume-section section-skills">
                  <h2 className="section-title">Technical & Core Skills</h2>
                  <div className="skills-grid">
                    {skills.map((skill) => (
                      <div key={skill.id} className="skill-item">
                        <span className="skill-name">{skill.name}</span>
                        {skill.proficiency && (
                          <span className="skill-level">({skill.proficiency})</span>
                        )}
                      </div>
                    ))}
                  </div>
                </section>
              ) : null;

            case 'experience':
              return experience && experience.length > 0 ? (
                <section key="experience" className="resume-section section-experience">
                  <h2 className="section-title">Professional Experience</h2>
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
                              ? `${exp.start_date} – ${exp.end_date || (exp.is_current ? 'Present' : '')}`
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
                  <h2 className="section-title">Education & Academic Background</h2>
                  <div className="education-list">
                    {education.map((edu) => (
                      <div key={edu.id} className="edu-item">
                        <div className="item-header-row">
                          <div className="item-title-col">
                            <span className="item-title">
                              {edu.degree} {edu.field ? `in ${edu.field}` : ''}
                            </span>
                            {edu.institution && (
                              <span className="item-company"> — {edu.institution}</span>
                            )}
                          </div>
                          <div className="item-date">
                            {edu.start_date || edu.end_date ? `${edu.start_date} – ${edu.end_date}` : ''}
                          </div>
                        </div>
                        {edu.gpa && <div className="edu-gpa">GPA / Honors: {edu.gpa}</div>}
                        {edu.description && <p className="item-description">{edu.description}</p>}
                      </div>
                    ))}
                  </div>
                </section>
              ) : null;

            case 'projects':
              return projects && projects.length > 0 ? (
                <section key="projects" className="resume-section section-projects">
                  <h2 className="section-title">Featured Projects</h2>
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
                  <h2 className="section-title">Certifications & Accreditations</h2>
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
                  <h2 className="section-title">Languages</h2>
                  <div className="languages-pills">
                    {languages.map((l) => (
                      <span key={l.id} className="lang-tag">
                        <strong>{l.language}</strong> ({l.proficiency})
                      </span>
                    ))}
                  </div>
                </section>
              ) : null;

            case 'custom_sections':
              return custom_sections && custom_sections.length > 0 ? (
                <div key="custom_sections">
                  {custom_sections.map((cSec) => (
                    <section key={cSec.id} className="resume-section section-custom">
                      <h2 className="section-title">{cSec.title || 'Additional Information'}</h2>
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
