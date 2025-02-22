"use client"

import { useEffect, useRef, useCallback } from 'react';

export default function useInfiniteScroll(onLoadMore: () => void) {
    const observer = useRef<IntersectionObserver | null>(null);
    const loadMoreRef = useCallback(
        (node: HTMLElement | null) => {
            if (observer.current) observer.current.disconnect();
            observer.current = new IntersectionObserver(entries => {
                if (entries[0].isIntersecting) {
                    onLoadMore();
                }
            });
            if (node) observer.current.observe(node);
        },
        [onLoadMore]
    );

    return [loadMoreRef];
}
