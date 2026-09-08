import React from 'react';
import styled from 'styled-components';

const Switch = () => {
  return (
    <StyledWrapper>
      <label className="switch">
        <input type="checkbox" />
        <span className="slider" />
        <span className="clouds_stars" />
      </label>
    </StyledWrapper>
  );
}

const StyledWrapper = styled.div`
  .switch {
    /* border: 2px solid rebeccapurple; */
    font-size: 17px;
    position: relative;
    display: inline-block;
    width: 3.5em;
    height: 2em;
  }
  .switch input {
    /* all: unset; */
    opacity: 0;
    width: 0;
    height: 0;
  }
  .slider {
    background-color: #2185d6;
    position: absolute;
    top: 0;
    left: 0;
    right: 0;
    bottom: 0;
    cursor: pointer;
    transition: 0.4s;
    border-radius: 30px;
    box-shadow: 0 0 0 rgba(33, 133, 214, 0);
    transition: all 0.4s ease;
  }
  .slider:hover {
    box-shadow: 0 0 15px rgba(33, 133, 214, 0.5);
  }

  .slider::before {
    position: absolute;
    content: "";
    height: 1.4em;
    width: 1.4em;
    border-radius: 50%;
    left: 10%;
    bottom: 15%;
    box-shadow: inset 15px -4px 0px 15px #fdf906;
    background-color: #28096b;
    transition: all 0.4s ease;
    transform-origin: center;
  }
  .slider:hover::before {
    transform: rotate(45deg);
  }
  .clouds_stars {
    position: absolute;
    content: "";
    border-radius: 50%;
    height: 10px;
    width: 10px;
    left: 70%;
    bottom: 50%;
    background-color: #fff;

    transition: all 0.3s;
    box-shadow:
      -12px 0 0 0 white,
      -6px 0 0 1.6px white,
      0.3px 16px 0 white,
      -6.5px 16px 0 white;
    filter: blur(0.55px);
  }
  .switch input:checked ~ .clouds_stars {
    transform: translateX(-20px);
    height: 2px;
    width: 2px;
    border-radius: 50%;
    left: 80%;
    top: 15%;
    background-color: #fff;
    backdrop-filter: blur(10px);
    transition: all 0.3s;
    box-shadow:
      -7px 10px 0 #fff,
      8px 15px 0 #fff,
      -17px 1px 0 #fff,
      -20px 10px 0 #fff,
      -7px 23px 0 #fff,
      -15px 25px 0 #fff;
    filter: none;
    animation: twinkle 2s infinite;
  }
  .switch input:checked + .slider {
    background-color: #28096b !important;
  }
  .switch input:checked + .slider::before {
    transform: translateX(100%);
    box-shadow: inset 8px -4px 0 0 #fff;
  }
  .switch input:checked + .slider:hover::before {
    transform: translateX(100%) rotate(-45deg);
  }
  @keyframes twinkle {
    0%,
    100% {
      opacity: 1;
    }
    50% {
      opacity: 0.5;
    }
  }`;

export default Switch;

