import { Center, Loader } from "@mantine/core";

/** Full-viewport centered loader — the route guards' pending state. */
export function LoadingFullPage() {
  return (
    <Center mih="100vh">
      <Loader />
    </Center>
  );
}
