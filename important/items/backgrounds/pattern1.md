import React from 'react';
import styled from 'styled-components';

const Pattern = () => {
  return (
    <StyledWrapper>
      <div className="grid-wrapper">
        <div className="grid-background" />
      </div>
    </StyledWrapper>
  );
}

const StyledWrapper = styled.div`
  .grid-wrapper {
    min-height: 100%;
    width: 100%;
    position: relative;
    background-color: #f8fafc;
  }

  .grid-background {
    position: absolute;
    top: 0;
    right: 0;
    bottom: 0;
    left: 0;
    z-index: 0;
    background-image: linear-gradient(to right, #e2e8f0 1px, transparent 1px),
      linear-gradient(to bottom, #e2e8f0 1px, transparent 1px);
    background-size: 20px 30px;
    -webkit-mask-image: radial-gradient(
      ellipse 70% 60% at 50% 0%,
      #000 60%,
      transparent 100%
    );
    mask-image: radial-gradient(
      ellipse 70% 60% at 50% 0%,
      #000 60%,
      transparent 100%
    );
  }`;

export default Pattern;

