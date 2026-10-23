import React from 'react';
import { DiagramViewer, type DiagramViewerProps } from './DiagramViewer';

export type GuideDiagramProps = DiagramViewerProps;

/**
 * GuideDiagram — Re-exports DiagramViewer to provide rich zoomable, pannable,
 * and expandable technical architecture diagrams across the documentation.
 */
export const GuideDiagram: React.FC<GuideDiagramProps> = (props) => {
  return <DiagramViewer {...props} />;
};

export { DiagramViewer };
export default GuideDiagram;
