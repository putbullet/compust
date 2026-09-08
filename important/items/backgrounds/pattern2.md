import React from 'react';
import styled from 'styled-components';

const Pattern = () => {
  return (
    <StyledWrapper>
      <div className="void-pulse">
        <span className="orbit-overlay" />
        <svg className="texture-filter">
          <filter id="void-texture">
            <feTurbulence result="noise" numOctaves={3} baseFrequency="0.02" type="turbulence" />
            <feGaussianBlur result="blur" stdDeviation={1} in="noise" />
            <feSpecularLighting result="specular" lightingColor="#ff66cc" specularExponent={20} specularConstant={1} surfaceScale={3} in="blur">
              <feDistantLight elevation={45} azimuth={90} />
            </feSpecularLighting>
            <feComposite result="lit" operator="over" in2="SourceGraphic" in="specular" />
            <feBlend mode="screen" in2="lit" in="SourceGraphic" />
          </filter>
        </svg>
      </div>
    </StyledWrapper>
  );
}

const StyledWrapper = styled.div`
  .void-pulse {
    width: 100%;
    height: 100%;
    background: linear-gradient(
      to bottom,
      rgba(30, 1, 15, 0.2) 0%,
      rgb(10, 10, 30) 0%,
      rgba(0, 0, 0, 1) 100%
    );
    filter: url(#void-texture);
    position: relative;
  }`;

export default Pattern;

