import React from 'react';
import styled from 'styled-components';

const Pattern = () => {
  return (
    <StyledWrapper>
      <div className="container" />
    </StyledWrapper>
  );
}

const StyledWrapper = styled.div`
  .container {
    width: 100%;
    height: 100%;
    background: repeating-linear-gradient(45deg, #92c9b1, #92c9b1 20px, #b3e0d2 20px, #b3e0d2 40px);
  }`;

export default Pattern;

