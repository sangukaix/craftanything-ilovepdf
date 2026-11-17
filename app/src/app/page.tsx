import './captured-home.css';
import './home-refinements.css';
import { capturedHome } from './captured-home';

export default function Page() {
  return <div className="captured-home lang-ko home" data-browser-supports="grid" dangerouslySetInnerHTML={{ __html: capturedHome }} />;
}
