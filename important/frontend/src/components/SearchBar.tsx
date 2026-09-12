import React from 'react';
import styled from 'styled-components';
import { Search, X, MapPin, Briefcase } from 'lucide-react';
import type { Country } from '../api/client';

import { useTranslation } from '../i18n';

interface SearchBarProps {
  searchTerm: string;
  onSearchChange: (val: string) => void;
  selectedCountry: number | null;
  onSelectCountry: (id: number | null) => void;
  countries: Country[];
  selectedRemote: string | null;
  onSelectRemote: (val: string | null) => void;
}

export const SearchBar: React.FC<SearchBarProps> = ({
  searchTerm,
  onSearchChange,
  selectedCountry,
  onSelectCountry,
  countries,
  selectedRemote,
  onSelectRemote,
}) => {
  const { t } = useTranslation();
  const remoteOptions = [
    { key: 'Remote', label: t.search.remote },
    { key: 'Hybrid', label: t.search.hybrid },
    { key: 'On-site', label: t.search.onsite },
  ];

  return (
    <StyledSearchWrapper>
      {/* Main Search Input */}
      <div className="input-glow-container">
        <Search size={20} className="search-icon" />
        <input
          type="text"
          value={searchTerm}
          onChange={(e) => onSearchChange(e.target.value)}
          placeholder={t.search.placeholder}
          aria-label={t.search.placeholder || 'Search vacancies, skills, and companies'}
          className="search-input"
        />
        {searchTerm && (
          <button className="clear-btn" onClick={() => onSearchChange('')} aria-label="Clear search">
            <X size={16} />
          </button>
        )}
      </div>

      {/* Quick Filters */}
      <div className="filters-row">
        {/* Country Pills */}
        <div className="filter-group">
          <MapPin size={15} className="filter-icon" />
          <div className="pills">
            <button
              className={`pill ${selectedCountry === null ? 'active' : ''}`}
              onClick={() => onSelectCountry(null)}
            >
              {t.search.allCountries}
            </button>
            {countries.map((c) => (
              <button
                key={c.id}
                className={`pill ${selectedCountry === c.id ? 'active' : ''}`}
                onClick={() => onSelectCountry(selectedCountry === c.id ? null : c.id)}
              >
                {c.name}
              </button>
            ))}
          </div>
        </div>

        {/* Remote Mode Pills */}
        <div className="filter-group">
          <Briefcase size={15} className="filter-icon" />
          <div className="pills">
            {remoteOptions.map((opt) => (
              <button
                key={opt.key}
                className={`pill ${selectedRemote === opt.key ? 'active' : ''}`}
                onClick={() => onSelectRemote(selectedRemote === opt.key ? null : opt.key)}
              >
                {opt.label}
              </button>
            ))}
          </div>
        </div>
      </div>
    </StyledSearchWrapper>
  );
};

const StyledSearchWrapper = styled.div`
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 18px;
  width: 100%;
  max-width: 820px;
  margin: 0 auto;

  .input-glow-container {
    display: flex;
    align-items: center;
    width: 100%;
    height: 56px;
    padding: 0 20px;
    background: rgba(18, 26, 42, 0.9);
    border: 1px solid rgba(59, 130, 246, 0.35);
    border-radius: 28px;
    box-shadow: 0 0 24px rgba(59, 130, 246, 0.15), 0 8px 32px rgba(0, 0, 0, 0.4);
    transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);

    &:focus-within {
      border-color: #3b82f6;
      box-shadow: 0 0 35px rgba(59, 130, 246, 0.35), 0 8px 32px rgba(0, 0, 0, 0.6);
      transform: translateY(-2px);
    }
  }

  .search-icon {
    color: #60a5fa;
    margin-right: 14px;
    flex-shrink: 0;
  }

  .search-input {
    width: 100%;
    height: 100%;
    border: none;
    outline: none;
    background: transparent;
    color: #ffffff;
    font-size: 1.05rem;
    font-weight: 500;

    &::placeholder {
      color: #94a3b8;
      font-weight: 400;
    }
  }

  .clear-btn {
    color: #94a3b8;
    padding: 6px;
    border-radius: 50%;
    display: flex;
    align-items: center;
    justify-content: center;
    transition: all 0.2s;

    &:hover {
      color: #ffffff;
      background: rgba(255, 255, 255, 0.1);
    }

    &:focus-visible {
      outline: 2px solid var(--border-focus);
      outline-offset: 2px;
    }
  }

  .filters-row {
    display: flex;
    flex-wrap: wrap;
    align-items: center;
    justify-content: center;
    gap: 16px;
    width: 100%;
  }

  .filter-group {
    display: flex;
    align-items: center;
    gap: 10px;
    background: rgba(15, 23, 42, 0.6);
    padding: 6px 14px;
    border-radius: 20px;
    border: 1px solid rgba(255, 255, 255, 0.06);
  }

  .filter-icon {
    color: #64748b;
  }

  .pills {
    display: flex;
    align-items: center;
    gap: 6px;
    flex-wrap: wrap;
  }

  .pill {
    padding: 4px 12px;
    font-size: 0.8rem;
    font-weight: 500;
    border-radius: 14px;
    color: #cbd5e1;
    background: rgba(255, 255, 255, 0.04);
    border: 1px solid rgba(255, 255, 255, 0.08);
    transition: all 0.2s ease;

    &:hover {
      color: #f8fafc;
      background: rgba(255, 255, 255, 0.1);
    }

    &:focus-visible {
      outline: 2px solid var(--border-focus);
      outline-offset: 2px;
    }

    &.active {
      color: #ffffff;
      background: #2563eb;
      border-color: #3b82f6;
      box-shadow: 0 0 12px rgba(37, 99, 235, 0.4);
    }
  }
`;
