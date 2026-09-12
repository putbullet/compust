import React from 'react';
import styled from 'styled-components';

interface LoaderProps {
  message?: string;
}

export const Loader: React.FC<LoaderProps> = ({ message = 'Loading opportunities...' }) => {
  return (
    <StyledLoaderWrapper>
      <div className="spinner">
        <div className="spinner1" />
      </div>
      <p className="loader-text">{message}</p>
    </StyledLoaderWrapper>
  );
};

const StyledLoaderWrapper = styled.div`
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 16px;
  padding: 40px 20px;

  .spinner {
    background-image: linear-gradient(rgb(186, 66, 255) 35%, rgb(0, 225, 255));
    width: 60px;
    height: 60px;
    animation: spinning8234 1.7s linear infinite;
    text-align: center;
    border-radius: 50px;
    filter: blur(1px);
    box-shadow: 0px -5px 20px 0px rgb(186, 66, 255), 0px 5px 20px 0px rgb(0, 225, 255);
  }

  .spinner1 {
    background-color: rgb(8, 12, 20);
    width: 60px;
    height: 60px;
    border-radius: 50px;
    filter: blur(8px);
  }

  .loader-text {
    font-size: 0.9rem;
    color: #94a3b8;
    font-weight: 500;
  }

  @keyframes spinning8234 {
    to {
      transform: rotate(360deg);
    }
  }
`;
