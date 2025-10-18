import React from 'react';

export const BrowserRouter = ({ children }: any) => <div>{children}</div>;
export const Routes = ({ children }: any) => {
  // Find the route for "/" path and render its element (the root route for tests)
  // In tests, we default to "/" path, so we render the first non-Navigate route element
  const routes = React.Children.toArray(children);
  const rootRoute = routes.find((child: any) => {
    return child?.props?.path === '/' && child?.props?.element;
  });
  if (rootRoute) {
    return <div>{(rootRoute as any).props.element}</div>;
  }
  // Fallback: render the first route with an element
  const firstRoute = routes.find((child: any) => child?.props?.element);
  return <div>{firstRoute ? (firstRoute as any).props.element : children}</div>;
};
export const Route = ({ element }: any) => <>{element}</>;
export const Navigate = () => null; // Don't render Navigate in tests
export const useNavigate = () => jest.fn();
export const useLocation = () => ({ pathname: '/', search: '', hash: '', state: null });
export const useParams = () => ({});
