import React, { useEffect } from "react";
import { getColumnDescriptions } from "../../app/store/config/actions";
import { useDispatch } from "react-redux";

const CustomTable = () => {
  const dispatch = useDispatch();
  useEffect(() => {
    dispatch(getColumnDescriptions());
  }, []);

  return <div>CustomTable</div>;
};

export default CustomTable;
