/*
 * Copyright (c) 2017-2020 Intel Corporation. All rights reserved.
 *
 * This software is available to you under a choice of one of two
 * licenses.  You may choose to be licensed under the terms of the GNU
 * General Public License (GPL) Version 2, available from the file
 * COPYING in the main directory of this source tree, or the
 * BSD license below:
 *
 *     Redistribution and use in source and binary forms, with or
 *     without modification, are permitted provided that the following
 *     conditions are met:
 *
 *      - Redistributions of source code must retain the above
 *        copyright notice, this list of conditions and the following
 *        disclaimer.
 *
 *      - Redistributions in binary form must reproduce the above
 *        copyright notice, this list of conditions and the following
 *        disclaimer in the documentation and/or other materials
 *        provided with the distribution.
 *
 * THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND,
 * EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF
 * MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND
 * NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS
 * BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN
 * ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN
 * CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
 * SOFTWARE.
 */

#include <stdlib.h>
#include <string.h>

#include "dpdk.h"

#define DPDK_DEF_CQ_SIZE (1024)


void dpdk_progress(struct dlist_entry *ep_list, struct util_wait *wait)
{
	/* Not Implemented */
}

void dpdk_cq_progress(struct util_cq *cq)
{
	ofi_mutex_lock(&cq->ep_list_lock);
	dpdk_progress(&cq->ep_list, cq->wait);
	ofi_mutex_unlock(&cq->ep_list_lock);
}

static int dpdk_cq_close(struct fid *fid)
{
	int ret;
	struct dpdk_cq *cq;

	cq = container_of(fid, struct dpdk_cq, util_cq.cq_fid.fid);
	ret = ofi_cq_cleanup(&cq->util_cq);
	if (ret)
		return ret;

	free(cq);
	return 0;
}

void dpdk_get_cq_info(uint64_t *flags,
		      uint64_t *data, uint64_t *tag)
{
	/* Not Implemented */
}

void dpdk_report_success(struct util_cq *cq)
{
	/* Not Impemented */
}

void dpdk_cq_report_error(struct util_cq *cq, int err)
{
	/* Not Implemented */
}

static struct fi_ops dpdk_cq_fi_ops = {
	.size = sizeof(struct fi_ops),
	.close = dpdk_cq_close,
	.bind = fi_no_bind,
	.control = fi_no_control,
	.ops_open = fi_no_ops_open,
};

int dpdk_cq_open(struct fid_domain *domain, struct fi_cq_attr *attr,
		 struct fid_cq **cq_fid, void *context)
{
	struct dpdk_cq *cq;
	struct fi_cq_attr cq_attr;
	int ret;

	cq = calloc(1, sizeof(*cq));
	if (!cq)
		return -FI_ENOMEM;

	if (!attr->size)
		attr->size = DPDK_DEF_CQ_SIZE;

	if (attr->wait_obj == FI_WAIT_NONE ||
	    attr->wait_obj == FI_WAIT_UNSPEC) {
		cq_attr = *attr;
		cq_attr.wait_obj = FI_WAIT_POLLFD;
		attr = &cq_attr;
	}

	ret = ofi_cq_init(&dpdk_prov, domain, attr, &cq->util_cq,
			  &dpdk_cq_progress, context);
	if (ret)
		goto free_cq;

	*cq_fid = &cq->util_cq.cq_fid;
	(*cq_fid)->fid.ops = &dpdk_cq_fi_ops;
	return 0;

free_cq:
	free(cq);
	return ret;
}


void dpdk_cntr_progress(struct util_cntr *cntr)
{
	ofi_mutex_lock(&cntr->ep_list_lock);
	dpdk_progress(&cntr->ep_list, cntr->wait);
	ofi_mutex_unlock(&cntr->ep_list_lock);
}

static struct util_cntr *
dpdk_get_cntr()
{
	/* Not Implemented */
	struct util_cntr *cntr;
	cntr = NULL;
	return cntr;
}

static void
dpdk_cntr_inc()
{
	/* Not Implemented */
}

void dpdk_report_cntr_success(struct util_cq *cq)
{
	/* Not Implemented */
}

void dpdk_cntr_incerr()
{
	/* Not Implemented */
}

int dpdk_cntr_open(struct fid_domain *fid_domain, struct fi_cntr_attr *attr,
		   struct fid_cntr **cntr_fid, void *context)
{
	struct util_cntr *cntr;
	struct fi_cntr_attr cntr_attr;
	int ret;

	cntr = calloc(1, sizeof(*cntr));
	if (!cntr)
		return -FI_ENOMEM;

	if (attr->wait_obj == FI_WAIT_NONE ||
	    attr->wait_obj == FI_WAIT_UNSPEC) {
		cntr_attr = *attr;
		cntr_attr.wait_obj = FI_WAIT_POLLFD;
		attr = &cntr_attr;
	}

	ret = ofi_cntr_init(&dpdk_prov, fid_domain, attr, cntr,
			    &dpdk_cntr_progress, context);
	if (ret)
		goto free;

	*cntr_fid = &cntr->cntr_fid;
	return FI_SUCCESS;

free:
	free(cntr);
	return ret;
}
